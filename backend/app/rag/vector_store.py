from pathlib import Path
import json

import faiss
import numpy as np


class VectorStore:
    def __init__(self, dimension: int):
        self.index = faiss.IndexFlatIP(dimension)
        self.texts: list[str] = []
        self.metadata: list[dict] = []

    def add(
        self,
        embeddings,
        texts: list[str],
        metadata: list[dict] | None = None,
    ):
        vectors = np.asarray(embeddings, dtype="float32")

        if len(vectors) != len(texts):
            raise ValueError("Number of embeddings must match number of texts.")

        if metadata is None:
            metadata = [{} for _ in texts]

        if len(metadata) != len(texts):
            raise ValueError("Number of metadata entries must match number of texts.")

        self.index.add(vectors)
        self.texts.extend(texts)
        self.metadata.extend(metadata)

    def search(self, embedding, top_k: int = 5):
        if not self.texts:
            return []

        vector = np.asarray(embedding, dtype="float32").reshape(1, -1)
        scores, indices = self.index.search(
            vector,
            min(top_k, len(self.texts)),
        )

        results = []

        for score, index in zip(scores[0], indices[0]):
            if index == -1:
                continue

            item = {
                "text": self.texts[index],
                "score": float(score),
            }

            if index < len(self.metadata):
                item.update(self.metadata[index])

            results.append(item)

        return results

    def save(self, directory: str):
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)

        faiss.write_index(
            self.index,
            str(path / "index.faiss"),
        )

        (path / "texts.txt").write_text(
            "\n\n---CHUNK---\n\n".join(self.texts),
            encoding="utf-8",
        )

        (path / "metadata.json").write_text(
            json.dumps(self.metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, directory: str, dimension: int):
        path = Path(directory)

        store = cls(dimension)

        store.index = faiss.read_index(
            str(path / "index.faiss"),
        )

        content = (path / "texts.txt").read_text(
            encoding="utf-8",
        )

        store.texts = (
            content.split("\n\n---CHUNK---\n\n")
            if content
            else []
        )

        metadata_path = path / "metadata.json"

        if metadata_path.exists():
            store.metadata = json.loads(
                metadata_path.read_text(encoding="utf-8")
            )
        else:
            store.metadata = [{} for _ in store.texts]

        return store
