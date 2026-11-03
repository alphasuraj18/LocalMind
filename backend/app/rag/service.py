from .document_store import DocumentStore
from .pipeline import RAGPipeline


class RAGService:
    def __init__(self):
        self.pipeline = RAGPipeline()
        self.documents = DocumentStore()

    def ingest(self, file_path: str):
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