from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .ollama import OllamaClient, OllamaError
from .schemas import ChatRequest, ChatResponse

app = FastAPI(title="LocalMind API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ollama = OllamaClient()

@app.get("/api/health")
async def health():
    status = await ollama.health()
    return {"app": "LocalMind", "ollama": status, "configured_model": settings.ollama_model}

@app.get("/api/models")
async def models():
    status = await ollama.health()
    return status

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        response = await ollama.chat(
            [m.model_dump() for m in request.history], request.message
        )
        return ChatResponse(response=response, model=settings.ollama_model)
    except OllamaError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
