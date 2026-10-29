from .pipeline import RAGPipeline


class RAGService:
    def __init__(self):
        self.pipeline = RAGPipeline()

    def ingest(self, file_path: str):
        return self.pipeline.ingest(file_path)

    def retrieve(self, query: str, top_k: int = 5):
        return self.pipeline.retrieve(query, top_k)
