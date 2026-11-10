from pathlib import Path
import hashlib
import threading

from .document_store import DocumentStore
from .pipeline import RAGPipeline


class DuplicateDocumentError(ValueError):
    """Raised when a document with identical content is already indexed."""


class RAGService:
    def __init__(self):
        self.pipeline = RAGPipeline()
        self.documents = DocumentStore()
        self.upload_dir = Path("data") / "uploads"
        self._lock = threading.RLock()
        self._backfill_content_hashes()

    @staticmethod
    def _file_hash(file_path: str | Path) -> str:
        digest = hashlib.sha256()
        with Path(file_path).open("rb") as file:
            for block in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    def _backfill_content_hashes(self):
        """Add hashes to older registry entries without re-ingesting documents."""
        for document in self.documents.get_all():
            if document.get("content_hash"):
                continue

            stored_file = self.upload_dir / document.get("filename", "")
            if not stored_file.is_file():
                continue

            try:
                content_hash = self._file_hash(stored_file)
                self.documents.update(
                    document["filename"],
                    {"content_hash": content_hash},
                )
            except OSError:
                # A missing/unreadable legacy upload must not prevent API startup.
                continue

    def ingest(self, file_path: str):
        filename = Path(file_path).name

        with self._lock:
            if self.documents.find(filename) is not None:
                raise DuplicateDocumentError(
                    f"Document '{filename}' is already indexed."
                )

            content_hash = self._file_hash(file_path)
            existing = self.documents.find_by_hash(content_hash)
            if existing is not None:
                raise DuplicateDocumentError(
                    f"This file has identical content to '{existing['filename']}'. "
                    "It is already indexed; no duplicate chunks were added."
                )

            result = self.pipeline.ingest(file_path)
            document = {
                "filename": result["file"],
                "chunks": result["chunks"],
                "embedding_dimension": result["embedding_dimension"],
                "content_hash": content_hash,
            }

            try:
                self.documents.add(document)
            except Exception:
                # Roll back vectors if the registry cannot be persisted.
                self.pipeline.delete_by_source(filename)
                raise

            return result

    def retrieve(self, query: str, top_k: int = 5):
        return self.pipeline.retrieve(query, top_k)

    def list_documents(self):
        return self.documents.get_all()

    def delete_document(self, filename: str):
        with self._lock:
            document = self.documents.find(filename)
            if document is None:
                return None

            expected_chunks = document.get("chunks", 0)
            removed_chunks = self.pipeline.delete_by_source(filename)

            if removed_chunks < expected_chunks:
                raise RuntimeError(
                    "Could not remove all indexed chunks for this document."
                )

            self.documents.delete(filename)

            return {
                "filename": filename,
                "deleted_chunks": removed_chunks,
            }
