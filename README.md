# LocalMind — Milestone 1

Offline AI Assistant with local inference. This milestone contains:
- FastAPI backend
- Ollama local-model interface
- Basic chat API with conversation history
- React + Vite chat UI
- Ollama health/model status

## Prerequisites
- Python 3.11+
- Node.js 20+
- Ollama installed locally

## 1. Start Ollama

Install Ollama, then pull the configured model:

```bash
ollama pull qwen2.5:3b
```

You can change the model in `backend/.env`.

## 2. Backend

Windows PowerShell:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python run.py
```

macOS/Linux:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python run.py
```

API: http://localhost:8000
Docs: http://localhost:8000/docs

## 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL shown in the terminal, normally http://localhost:5173.

## API

`GET /api/health` — application + Ollama health

`GET /api/models` — locally available Ollama models

`POST /api/chat`

```json
{
  "message": "Explain binary search",
  "history": []
}
```

## Next milestone

RAG ingestion and retrieval: PDF/TXT/DOCX → chunking → local embeddings → FAISS → citations.
