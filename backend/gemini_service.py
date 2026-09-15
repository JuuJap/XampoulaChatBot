import math
import re
import threading
from pathlib import Path

from google import genai

from config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    GEMINI_THINKING_LEVEL,
    SYSTEM_PROMPT_FILE,
)


class GeminiServiceError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int = 502,
        code: str = "provider_error",
        retry_after: int | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.retry_after = retry_after


class GeminiService:
    """
    Mantém o histórico completo da Interactions API somente na memória do backend.
    Nada do chat é salvo no MySQL; apenas respostas que o usuário clicar em Salvar.
    """

    def __init__(self):
        self._client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
        self._histories: dict[str, list[dict]] = {}
        self._lock = threading.RLock()

    @property
    def configured(self) -> bool:
        return bool(GEMINI_API_KEY and self._client)

    @property
    def model(self) -> str:
        return GEMINI_MODEL

    def _system_prompt(self) -> str:
        try:
            prompt = Path(SYSTEM_PROMPT_FILE).read_text(encoding="utf-8").strip()
            if prompt:
                return prompt
        except OSError:
            pass
        return "Responda sempre em português do Brasil de forma clara e útil."

    def reset_session(self, session_id: str) -> None:
        with self._lock:
            self._histories.pop(session_id, None)

    def generate(self, session_id: str, question: str) -> str:
        if not self.configured:
            raise GeminiServiceError(
                "A chave do Gemini não está configurada em backend/.env.",
                status_code=503,
                code="gemini_not_configured",
            )

        user_step = {
            "type": "user_input",
            "content": [{"type": "text", "text": question}],
        }

        with self._lock:
            history = list(self._histories.get(session_id, []))

        try:
            interaction = self._client.interactions.create(
                model=GEMINI_MODEL,
                input=history + [user_step],
                store=False,
                system_instruction=self._system_prompt(),
                generation_config={
                    "temperature": 0.8,
                    "thinking_level": GEMINI_THINKING_LEVEL,
                },
            )

            answer = (interaction.output_text or "").strip()
            if not answer:
                raise GeminiServiceError(
                    "O Gemini não retornou texto nesta resposta.",
                    status_code=502,
                    code="empty_response",
                )

            generated_steps = [
                step.model_dump(exclude_none=True) for step in (interaction.steps or [])
            ]

            with self._lock:
                self._histories[session_id] = history + [user_step] + generated_steps

            return answer

        except GeminiServiceError:
            raise
        except Exception as exc:
            raise self._translate_error(exc) from exc

    @staticmethod
    def _translate_error(exc: Exception) -> GeminiServiceError:
        raw = str(exc)
        lowered = raw.lower()

        retry_after = None
        match = re.search(r"retry\s+in\s+([0-9.]+)s", raw, flags=re.IGNORECASE)
        if match:
            retry_after = max(1, math.ceil(float(match.group(1))))

        if "429" in raw or "too_many_requests" in lowered or "resource_exhausted" in lowered:
            if retry_after:
                message = (
                    f"O limite da API Gemini foi atingido. "
                    f"Tente novamente em cerca de {retry_after} segundos."
                )
            else:
                message = (
                    "A cota da API Gemini deste projeto foi atingida. "
                    "Aguarde a renovação do limite ou verifique a cota no Google AI Studio."
                )
            return GeminiServiceError(
                message,
                status_code=429,
                code="rate_limit",
                retry_after=retry_after,
            )

        if "401" in raw or "403" in raw or "api key" in lowered or "permission_denied" in lowered:
            return GeminiServiceError(
                "A chave da API Gemini é inválida ou não tem permissão para este projeto.",
                status_code=401,
                code="invalid_api_key",
            )

        if "404" in raw or "not_found" in lowered:
            return GeminiServiceError(
                f"O modelo {GEMINI_MODEL} não está disponível para esta chave/projeto.",
                status_code=502,
                code="model_unavailable",
            )

        return GeminiServiceError(
            "Não foi possível obter uma resposta do Gemini agora. Tente novamente em instantes.",
            status_code=502,
            code="provider_error",
        )
