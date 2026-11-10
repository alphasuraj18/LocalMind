from pathlib import Path
import json


class DocumentStore:
    """Persistent registry for documents indexed by LocalMind."""

    def __init__(self, path: str = "data/rag/documents.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.documents = self._load()

    def _load(self) -> list[dict]:
        if not self.path.exists():
            return []

        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                raise ValueError("Document registry must contain a JSON list.")
            return data
        except (json.JSONDecodeError, OSError) as exc:
            raise RuntimeError(f"Could not load document registry: {exc}") from exc

    def _save(self):
        """Write registry atomically so an interrupted write cannot truncate it."""
        temporary_path = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary_path.write_text(
            json.dumps(self.documents, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary_path.replace(self.path)

    def add(self, document: dict):
        if self.find(document.get("filename", "")) is not None:
            raise ValueError(f"Document '{document.get('filename')}' is already indexed.")

        self.documents.append(document)
        try:
            self._save()
        except Exception:
            self.documents.pop()
            raise

    def update(self, filename: str, fields: dict) -> bool:
        document = self.find(filename)
        if document is None:
            return False

        previous = document.copy()
        document.update(fields)
        try:
            self._save()
        except Exception:
            document.clear()
            document.update(previous)
            raise
        return True

    def get_all(self) -> list[dict]:
        return self.documents

    def find(self, filename: str) -> dict | None:
        return next(
            (doc for doc in self.documents if doc.get("filename") == filename),
            None,
        )

    def find_by_hash(self, content_hash: str) -> dict | None:
        if not content_hash:
            return None

        return next(
            (doc for doc in self.documents if doc.get("content_hash") == content_hash),
            None,
        )

    def delete(self, filename: str) -> bool:
        original = self.documents
        self.documents = [
            doc for doc in original if doc.get("filename") != filename
        ]

        if len(self.documents) == len(original):
            return False

        try:
            self._save()
        except Exception:
            self.documents = original
            raise
        return True
