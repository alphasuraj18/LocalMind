import httpx
from .config import settings

class OllamaError(RuntimeError):
    pass

class OllamaClient:
    def __init__(self):
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.model = settings.ollama_model
        self.timeout = settings.ollama_timeout

    async def health(self) -> dict:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(f"{self.base_url}/api/tags")
                r.raise_for_status()
                models = [m.get("name") for m in r.json().get("models", [])]
                return {"connected": True, "models": models}
        except (httpx.HTTPError, ValueError) as exc:
            return {"connected": False, "models": [], "error": str(exc)}

    async def chat(self, history: list[dict], message: str) -> str:
        messages = history + [{"role": "user", "content": message}]
        payload = {"model": self.model, "messages": messages, "stream": False}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                r = await client.post(f"{self.base_url}/api/chat", json=payload)
                r.raise_for_status()
                data = r.json()
                content = data.get("message", {}).get("content")
                if not content:
                    raise OllamaError("Ollama returned an empty response")
                return content
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:500]
            raise OllamaError(f"Ollama request failed: {exc.response.status_code} {detail}") from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise OllamaError(f"Could not reach Ollama: {exc}") from exc
