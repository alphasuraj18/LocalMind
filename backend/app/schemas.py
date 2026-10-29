from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant|system)$")
    content: str = Field(min_length=1)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10000)
    history: list[ChatMessage] = Field(default_factory=list)
    use_rag: bool = False
    top_k: int = Field(default=5, ge=1, le=10)


class ChatResponse(BaseModel):
    response: str
    model: str
    provider: str = "ollama"
    sources: list[dict] = Field(default_factory=list)
