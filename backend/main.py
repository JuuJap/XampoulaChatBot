from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import database
from config import APP_HOST, APP_PORT, PROJECT_ROOT
from database import DatabaseUnavailable
from gemini_service import GeminiService, GeminiServiceError
from schemas import ChatRequest, SaveRequest, SessionRequest


gemini = GeminiService()
database_ready = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    global database_ready
    try:
        database.initialize()
        database_ready = True
        print("[OK] MySQL conectado e tabelas verificadas.")
    except Exception as exc:
        database_ready = False
        print(f"[AVISO] MySQL indisponível: {exc}")
        print("[INFO] O chat continua funcionando, mas Salvar ficará indisponível.")
    yield


app = FastAPI(
    title="Xampoula Chat API",
    version="2.0.0",
    lifespan=lifespan,
)

# O frontend agora é servido pelo próprio FastAPI: sem Live Server e sem CORS.
app.mount("/css", StaticFiles(directory=PROJECT_ROOT / "css"), name="css")
app.mount("/js", StaticFiles(directory=PROJECT_ROOT / "js"), name="js")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(PROJECT_ROOT / "index.html")


@app.get("/api/health")
def health():
    db_online = database.ping()
    return {
        "api": True,
        "gemini_configured": gemini.configured,
        "model": gemini.model,
        "database": db_online,
    }


@app.post("/api/chat")
def chat(request: ChatRequest):
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail={"message": "Digite uma pergunta."})

    try:
        answer = gemini.generate(request.session_id, question)
        return {"answer": answer, "model": gemini.model}
    except GeminiServiceError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={
                "code": exc.code,
                "message": str(exc),
                "retry_after": exc.retry_after,
            },
        ) from exc


@app.post("/api/chat/reset")
def reset_chat(request: SessionRequest):
    gemini.reset_session(request.session_id)
    return {"success": True}


@app.post("/api/save")
def save_answer(request: SaveRequest):
    try:
        response_id = database.save_response(
            request.session_id,
            request.question.strip(),
            request.answer.strip(),
        )
        return {
            "success": True,
            "id": response_id,
            "message": "Resposta salva no MySQL.",
        }
    except DatabaseUnavailable as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "database_unavailable",
                "message": "Não foi possível acessar o MySQL. Verifique se ele está iniciado no XAMPP.",
            },
        ) from exc


@app.get("/api/saved/{session_id}")
def get_saved_answers(session_id: str):
    try:
        return {"saved": database.list_responses(session_id)}
    except DatabaseUnavailable as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "database_unavailable",
                "message": "MySQL indisponível.",
            },
        ) from exc


@app.delete("/api/saved/{response_id}")
def delete_saved_answer(response_id: int, session_id: str = Query(..., max_length=64)):
    try:
        deleted = database.delete_response(session_id, response_id)
        if not deleted:
            raise HTTPException(status_code=404, detail={"message": "Resposta não encontrada."})
        return {"success": True}
    except DatabaseUnavailable as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": "database_unavailable", "message": "MySQL indisponível."},
        ) from exc


@app.delete("/api/saved/session/{session_id}")
def clear_saved_answers(session_id: str):
    try:
        deleted = database.clear_responses(session_id)
        return {"success": True, "deleted": deleted}
    except DatabaseUnavailable as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": "database_unavailable", "message": "MySQL indisponível."},
        ) from exc


@app.post("/api/session/close")
def close_session(request: SessionRequest):
    gemini.reset_session(request.session_id)
    try:
        database.close_session(request.session_id)
    except DatabaseUnavailable:
        # Fechar a aba não deve gerar erro visível caso o MySQL já tenha parado.
        pass
    return {"success": True}


if __name__ == "__main__":
    import uvicorn

    print(f"[INFO] Abra no navegador: http://{APP_HOST}:{APP_PORT}")
    uvicorn.run(
        "main:app",
        host=APP_HOST,
        port=APP_PORT,
        reload=False,
    )
