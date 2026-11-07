from pathlib import Path

from .document_store import DocumentStore
from .pipeline import RAGPipeline


class RAGService:
    def __init__(self):
        self.pipeline = RAGPipeline()
        self.documents = DocumentStore()

    def ingest(self, file_path: str):
        filename = Path(file_path).name

        if self.documents.find(filename) is not None:
            raise ValueError(
                f"Document '{filename}' is already indexed."
            )
        result = self.pipeline.ingest(file_path)

        self.documents.add(
            {
                "filename": result["file"],
                "chunks": result["chunks"],
                "embedding_dimension": result["embedding_dimension"],
            }
        )

        return result

    def retrieve(self, query: str, top_k: int = 5):
        return self.pipeline.retrieve(query, top_k)

    def list_documents(self):
        return self.documents.get_all()

    def delete_document(self, filename: str):
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