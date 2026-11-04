# LocalMind

**A local-first AI assistant with private inference, document-based retrieval, and a clean workspace UI.**

LocalMind is a personal project exploring how to build an AI assistant that runs on your own machine. It connects a React frontend to a FastAPI backend and a locally hosted language model through [Ollama](https://ollama.com/). The current implementation supports chat, local model status, and retrieval-augmented conversations over uploaded PDF, DOCX, and TXT files.

## Application Preview

![LocalMind Dashboard](<img width="1919" height="1079" alt="Screenshot 2026-11-04 224208" src="https://github.com/user-attachments/assets/9d2d555c-1351-4faf-92f0-0d443167a746" />
)

> **Project status:** Active development. The current build includes local chat and a first multi-document RAG implementation. The document library and richer source-inspection experience are being developed incrementally.

## What it does

- **Local LLM chat:** Send messages to a model served by Ollama on your machine.
- **Conversation context:** Pass chat history to the backend so the model can use previous turns.
- **Document ingestion:** Upload PDF, DOCX, and TXT files for text extraction and indexing.
- **Retrieval-augmented generation (RAG):** Split extracted text into overlapping chunks, embed the chunks locally, retrieve relevant passages with FAISS, and include the retrieved context in the model prompt.
- **Source metadata:** Return source filename, chunk number, and similarity score with retrieved passages.
- **Local runtime status:** Check Ollama connectivity and the models available on the local Ollama instance.
- **Workspace UI:** React-based dark interface with Markdown rendering, upload controls, RAG toggle, and retrieval-count selection.

## Architecture

```text
┌──────────────────────────────┐
│       React + Vite UI        │
│  Chat · Upload · RAG controls │
└──────────────┬───────────────┘
               │ HTTP
┌──────────────▼───────────────┐
│        FastAPI backend       │
│       /api/chat              │
│       /api/health            │
│       /api/models            │
│       /api/rag/upload        │
└──────────────┬───────────────┘
               │
       ┌───────┴────────┐
       │                │
┌──────▼───────┐  ┌─────▼───────────────────┐
│    Ollama    │  │       RAG pipeline      │
│ Local model  │  │ Load → Chunk → Embed    │
│ inference    │  │ → FAISS search → Context│
└──────────────┘  └─────────────────────────┘
```

### RAG flow

1. Upload a supported document.
2. Extract text from the file.
3. Split text into chunks (currently 800 characters with 120 characters of overlap).
4. Generate normalized embeddings with Sentence Transformers using `all-MiniLM-L6-v2`.
5. Store vectors in a FAISS inner-product index.
6. Embed the user's question and retrieve the top-`k` matching chunks.
7. Add retrieved passages to the prompt sent to Ollama.
8. Return the answer and retrieved source metadata to the frontend.

## Tech stack

| Layer | Technologies |
|---|---|
| Frontend | React, Vite, JavaScript, CSS |
| Markdown | react-markdown, remark-gfm |
| Backend API | Python, FastAPI, Uvicorn |
| Local inference | Ollama |
| Default model | `qwen2.5:3b` |
| Document parsing | PyMuPDF, python-docx |
| Embeddings | Sentence Transformers, `all-MiniLM-L6-v2` |
| Vector search | FAISS (CPU), NumPy |

## Getting started

### Prerequisites

Install the following before running the project:

- Python 3.10+
- Node.js (the installed Vite version may require a recent Node 20 release or Node 22+)
- [Ollama](https://ollama.com/)
- Git

### 1. Download a local model

Start Ollama, then pull the default model:

```bash
ollama pull qwen2.5:3b
```

The backend defaults to `http://localhost:11434` and model `qwen2.5:3b`. These can be overridden with backend environment variables:

- `OLLAMA_BASE_URL`
- `OLLAMA_MODEL`
- `OLLAMA_TIMEOUT`

### 2. Set up the backend

From the repository root:

**Windows PowerShell**

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

**macOS / Linux**

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

The API starts at:

- API base: http://127.0.0.1:8000
- Interactive API docs: http://127.0.0.1:8000/docs

The RAG embedding model is downloaded by Sentence Transformers on first initialization if it is not already present in the local cache.

### 3. Set up the frontend

Open a second terminal from the repository root:

```bash
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite (normally http://localhost:5173).

### 4. Try it

1. Confirm the top bar reports the local model as connected.
2. Send a regular message to test local chat.
3. Upload a `.pdf`, `.docx`, or `.txt` document.
4. Keep the RAG toggle enabled and ask a question about the document.
5. Adjust the Top-K selector to control how many chunks are retrieved.

## API overview

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/health` | Check application and Ollama connectivity |
| `GET` | `/api/models` | List models available through Ollama |
| `POST` | `/api/rag/upload` | Upload and index a PDF, DOCX, or TXT file |
| `POST` | `/api/chat` | Generate a response, optionally using retrieved context |

### Chat request example

```json
{
  "message": "Summarize the main points in this document.",
  "history": [],
  "use_rag": true,
  "top_k": 3
}
```

RAG fields are optional according to the API schema; when RAG is enabled, the backend retrieves up to the requested number of chunks and provides them as context to the model.

## Project structure

```text
LocalMind/
├── backend/
│   ├── app/
│   │   ├── rag/
│   │   │   ├── loaders.py
│   │   │   ├── chunker.py
│   │   │   ├── embedder.py
│   │   │   ├── vector_store.py
│   │   │   ├── pipeline.py
│   │   │   ├── document_store.py
│   │   │   └── service.py
│   │   ├── main.py
│   │   ├── ollama.py
│   │   ├── config.py
│   │   └── schemas.py
│   ├── requirements.txt
│   └── run.py
└── frontend/
    ├── src/
    │   ├── main.jsx
    │   └── styles.css
    └── package.json
```

## Privacy and local execution

LocalMind is designed around local inference: the application sends prompts to the Ollama service configured on your machine rather than to a hosted model API. The embedding model is also run through Sentence Transformers locally after it has been downloaded.

A few practical notes:

- The first embedding-model run may need an internet connection to download model files.
- Uploaded documents and the FAISS index are stored by the backend in its local data directories.
- Do not upload sensitive documents unless you understand and control the security of the machine and its local storage.
- This project does not currently provide authentication or multi-user access controls. Keep the development server bound to a trusted local environment.

## Current limitations

- The RAG pipeline currently uses a simple character-based chunker and dense vector similarity search.
- Retrieval quality depends on the uploaded document's extracted text and the embedding model.
- Document deletion and full per-document vector-index management are not yet part of the current API.
- The backend stores a persistent FAISS index and document metadata locally; the frontend's selected-document indicator is currently client state and may reset on a page refresh.
- Model streaming, advanced reranking, and production deployment hardening are not currently implemented.

## Roadmap

- [ ] Persistent document library and document lifecycle management
- [ ] Expandable source cards with retrieved text and similarity visualization
- [ ] Better document-level indexing and deletion
- [ ] Streaming chat responses and stop-generation controls
- [ ] RAG evaluation and retrieval-quality benchmarks
- [ ] Model comparison and local inference benchmarking
- [ ] More robust settings and configuration UI
- [ ] Automated backend and frontend tests

## Contributing

This is an actively evolving learning and engineering project. Suggestions, bug reports, and pull requests are welcome. For larger changes, open an issue first to discuss the proposed approach.

## License

No license has been specified yet. Unless a license is added to this repository, the default copyright rules apply and reuse is not automatically permitted.
