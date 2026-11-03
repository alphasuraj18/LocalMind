from pathlib import Path
import json


class DocumentStore:
    def __init__(self, path: str = "data/rag/documents.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.documents = self._load()

    def _load(self) -> list[dict]:
        if not self.path.exists():
            return []

        try:
            return json.loads(
                self.path.read_text(encoding="utf-8")
            )
        except (json.JSONDecodeError, OSError):
            return []

    def _save(self):
        self.path.write_text(
            json.dumps(
                self.documents,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def add(self, document: dict):
        self.documents.append(document)
        self._save()

    def get_all(self) -> list[dict]:
        return self.documents

    def find(self, filename: str) -> dict | None:
        return next(
            (
                document
                for document in self.documents
                if document.get("filename") == filename
            ),
            None,
        )

    def delete(self, filename: str) -> bool:
        original_count = len(self.documents)

        self.documents = [
            document
            for document in self.documents
            if document.get("filename") != filename
        ]

        changed = len(self.documents) < original_count

        if changed:
            self._save()

        return changed