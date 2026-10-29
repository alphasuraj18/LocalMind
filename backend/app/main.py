from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .ollama import OllamaClient, OllamaError
from .schemas import ChatRequest, ChatResponse
from .rag.service import RAGService


app = FastAPI(title="LocalMind API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ollama = OllamaClient()
rag = RAGService()

UPLOAD_DIR = Path("data") / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}


@app.get("/api/health")
async def health():
    status = await ollama.health()
    return {
        "app": "LocalMind",
        "ollama": status,
        "configured_model": settings.ollama_model,
    }


@app.get("/api/models")
async def models():
    status = await ollama.health()
    return status


@app.post("/api/rag/upload")
async def upload_document(file: UploadFile = File(...)):
    extension = Path(file.filename or "").suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Supported types: PDF, DOCX, TXT.",
        )

    filename = Path(file.filename).name
    destination = UPLOAD_DIR / filename

    try:
        content = await file.read()
        destination.write_bytes(content)

        result = rag.ingest(str(destination))

        return {
            "message": "Document ingested successfully.",
            **result,
        }

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Document ingestion failed: {exc}",
        ) from exc


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        history = [m.model_dump() for m in request.history]
        message = request.message
        sources = []

        if request.use_rag:
            results = rag.retrieve(message, top_k=request.top_k)

            if results:
                context = "\n\n".join(
                    f"[Source {i + 1}]\n{item['text']}"
                    for i, item in enumerate(results)
                )

                message = f"""Use the following retrieved context to answer the user's question.

Retrieved context:
{context}

User question:
{request.message}

Answer based on the retrieved context when relevant. If the context does not contain enough information, say so clearly."""

                sources = results

        response = await ollama.chat(history, message)

        return ChatResponse(
            response=response,
            model=settings.ollama_model,
            sources=sources,
        )

    except OllamaError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

