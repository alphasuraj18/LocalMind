from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .ollama import OllamaClient, OllamaError
from .schemas import ChatRequest, ChatResponse
from .rag.service import RAGService, DuplicateDocumentError
from .rag.grounding import has_valid_source_citations


app = FastAPI(title="LocalMind API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
    ],
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
    return await ollama.health()


@app.post("/api/rag/upload")
async def upload_document(file: UploadFile = File(...)):
    original_name = file.filename or ""
    extension = Path(original_name).suffix.lower()
    filename = Path(original_name).name

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Supported types: PDF, DOCX, TXT.",
        )

    if not filename or filename in {".", ".."}:
        raise HTTPException(status_code=400, detail="Invalid filename.")

    if rag.documents.find(filename) is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Document '{filename}' is already indexed.",
        )

    destination = UPLOAD_DIR / filename
    created_destination = False

    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="The uploaded file is empty.")

        # Avoid overwriting an existing file that may be an orphan or user data.
        if destination.exists():
            raise HTTPException(
                status_code=409,
                detail=f"A file named '{filename}' already exists in the upload directory.",
            )

        destination.write_bytes(content)
        created_destination = True

        result = rag.ingest(str(destination))
        return {
            "message": "Document ingested successfully.",
            **result,
        }

    except DuplicateDocumentError as exc:
        if created_destination and destination.exists():
            destination.unlink()
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    except HTTPException:
        if created_destination and destination.exists():
            destination.unlink()
        raise

    except ValueError as exc:
        if created_destination and destination.exists():
            destination.unlink()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    except Exception as exc:
        if created_destination and destination.exists():
            destination.unlink()
        raise HTTPException(
            status_code=500,
            detail=f"Document ingestion failed: {exc}",
        ) from exc

    finally:
        await file.close()


@app.get("/api/rag/documents")
async def list_documents():
    return {"documents": rag.list_documents()}


@app.delete("/api/rag/documents/{filename}")
async def delete_document(filename: str):
    safe_filename = Path(filename).name

    if not safe_filename or safe_filename != filename:
        raise HTTPException(status_code=400, detail="Invalid document filename.")

    try:
        result = rag.delete_document(safe_filename)
        if result is None:
            raise HTTPException(status_code=404, detail="Document not found.")

        uploaded_file = UPLOAD_DIR / safe_filename
        if uploaded_file.is_file():
            uploaded_file.unlink()

        return {
            "message": "Document deleted successfully.",
            **result,
        }

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Document deletion failed: {exc}",
        ) from exc


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        history = [message.model_dump() for message in request.history]
        message = request.message
        sources = []

        if request.use_rag:
            results = rag.retrieve(message, top_k=request.top_k)

            # Never silently answer from the base model when retrieval found no evidence.
            if not results:
                return ChatResponse(
                    response=(
                        "I couldn't find relevant information in your indexed "
                        "documents. Try rephrasing your question or uploading "
                        "a document that covers this topic."
                    ),
                    model=settings.ollama_model,
                    sources=[],
                )

            sources = results
            context = "\n\n".join(
                f"[Source {index + 1}]\n{item['text']}"
                for index, item in enumerate(results)
            )
            message = f"""You are answering a question using a closed set of retrieved document passages.

Rules:
- Use only the retrieved context below for factual claims about the user's documents.
- Do not use outside knowledge to fill gaps.
- Cite each factual paragraph with one or more exact source markers, such as [Source 1].
- Only cite source numbers that appear in the retrieved context.
- If the passages do not contain enough information, say that the documents do not provide enough information. Do not guess.
- Do not invent quotations, facts, filenames, or source numbers.

Retrieved context:
{context}

User question:
{request.message}

Write a clear, concise answer grounded in the retrieved context."""

        response = await ollama.chat(history, message)

        if request.use_rag and not has_valid_source_citations(
            response, source_count=len(sources)
        ):
            response = (
                "I retrieved document passages, but couldn't produce an answer "
                "with valid source citations. Please rephrase the question or "
                "try again. You can inspect the retrieved passages below."
            )

        return ChatResponse(
            response=response,
            model=settings.ollama_model,
            sources=sources,
        )

    except OllamaError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
