import os
from pathlib import Path

from .chunker import chunk_text
from .embedder import Embedder
from .loaders import load_document
from .vector_store import VectorStore


class RAGPipeline:
    def __init__(self, min_similarity_score: float | None = None):
        self.embedder = Embedder()
        self.store = None
        self.data_dir = Path("data") / "rag"

        configured_threshold = (
            os.getenv("LOCALMIND_MIN_RETRIEVAL_SCORE", "0.45")
            if min_similarity_score is None
            else min_similarity_score
        )
        try:
            self.min_similarity_score = float(configured_threshold)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "LOCALMIND_MIN_RETRIEVAL_SCORE must be a valid number."
            ) from exc

        if not -1.0 <= self.min_similarity_score <= 1.0:
            raise ValueError(
                "Minimum retrieval score must be between -1.0 and 1.0."
            )

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

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        min_similarity_score: float | None = None,
    ):
        if self.store is None or not self.store.texts:
            return []

        threshold = (
            self.min_similarity_score
            if min_similarity_score is None
            else float(min_similarity_score)
        )
        if not -1.0 <= threshold <= 1.0:
            raise ValueError("Minimum retrieval score must be between -1.0 and 1.0.")

        query_embedding = self.embedder.encode_query(query)[0]

        results = self.store.search(
            query_embedding,
            top_k=top_k,
        )

        # FAISS uses normalized embeddings here, so these are cosine-like
        # similarity scores, not probabilities. Keep only results meeting
        # the configured minimum score.
        return [
            result
            for result in results
            if float(result.get("score", -1.0)) >= threshold
        ]

    def delete_by_source(self, source_name: str) -> int:
        if self.store is None:
            return 0

        removed_count = self.store.delete_by_source(source_name)

        if removed_count > 0:
            self.store.save(str(self.data_dir))

        return removed_count
