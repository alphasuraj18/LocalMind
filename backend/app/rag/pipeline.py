from pathlib import Path

from .chunker import chunk_text
from .embedder import Embedder
from .loaders import load_document
from .vector_store import VectorStore


class RAGPipeline:
    def __init__(self):
        self.embedder = Embedder()
        self.store = None
        self.data_dir = Path("data") / "rag"

        self._load_store()

    def _load_store(self):
        index_path = self.data_dir / "index.faiss"
        texts_path = self.data_dir / "texts.txt"

        if not index_path.exists() or not texts_path.exists():
            return

        try:
            dimension = self.embedder.encode(["test"]).shape[1]

            self.store = VectorStore.load(
                str(self.data_dir),
                dimension,
            )
        except Exception:
            self.store = None

    def ingest(self, file_path: str):
        text = load_document(file_path)
        chunks = chunk_text(text)

        if not chunks:
            raise ValueError("No text could be extracted from the document.")

        embeddings = self.embedder.encode(chunks)

        source_name = Path(file_path).name

        metadata = [
            {
                "source": source_name,
                "chunk": index + 1,
            }
            for index in range(len(chunks))
        ]

        if self.store is None:
            self.store = VectorStore(embeddings.shape[1])

        self.store.add(
            embeddings,
            chunks,
            metadata,
        )

        self.store.save(str(self.data_dir))

        return {
            "file": source_name,
            "chunks": len(chunks),
            "embedding_dimension": embeddings.shape[1],
        }

    def retrieve(self, query: str, top_k: int = 5):
        if self.store is None or not self.store.texts:
            return []

        query_embedding = self.embedder.encode_query(query)[0]

        return self.store.search(
            query_embedding,
            top_k=top_k,
        )
