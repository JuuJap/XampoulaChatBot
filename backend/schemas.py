from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=64)
    question: str = Field(min_length=1, max_length=4000)


class SaveRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=64)
    question: str = Field(min_length=1, max_length=4000)
    answer: str = Field(min_length=1, max_length=50000)


class SessionRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=64)
