import sys
import json
import csv
import time

from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.rag.embedder import Embedder
from app.rag.vector_store import VectorStore
from app.rag.evaluation import (
    precision_at_k,
    recall_at_k,
    mean_reciprocal_rank,
)
from app.rag.confidence import answerability_metrics

DATASET_PATH = ROOT / "backend" / "tests" / "retrieval_dataset.json"
REPORT_DIR = ROOT / "backend" / "reports"
TOP_K = 3

DOCUMENTS = [
    {
        "source": "python",
        "chunk": 1,
        "text": (
            "Python is a popular programming language used in "
            "machine learning, automation, and software development."
        ),
    },
    {
        "source": "python",
        "chunk": 2,
        "text": (
            "Python supports data analysis through libraries such as "
            "NumPy and Pandas, which process and analyze datasets."
        ),
    },
    {
        "source": "ml",
        "chunk": 1,
        "text": (
            "Supervised learning trains a model using labelled examples "
            "to predict outputs for unseen data."
        ),
    },
    {
        "source": "ml",
        "chunk": 2,
        "text": (
            "A training dataset contains examples used by a machine "
            "learning algorithm to learn patterns and parameters."
        ),
    },
    {
        "source": "database",
        "chunk": 1,
        "text": (
            "A relational database organizes information into tables "
            "containing rows and columns with relationships between them."
        ),
    },
    {
        "source": "database",
        "chunk": 2,
        "text": (
            "SQL is used to query, insert, update, and manage data "
            "stored in relational databases."
        ),
    },
]


def chunk_id(item):
    return f'{item["source"]}::{item["chunk"]}'


def main():
    dataset = json.loads(
        DATASET_PATH.read_text(encoding="utf-8-sig")
    )

    if not dataset:
        raise ValueError("Evaluation dataset is empty.")

    print("\nLOCALMIND RETRIEVAL DIAGNOSTICS")
    print("=" * 65)

    # Measure embedding model initialization
    start = time.perf_counter()
    embedder = Embedder()
    model_load_ms = (time.perf_counter() - start) * 1000

    # Measure corpus embedding
    texts = [item["text"] for item in DOCUMENTS]

    start = time.perf_counter()
    embeddings = embedder.encode(texts)
    corpus_embedding_ms = (time.perf_counter() - start) * 1000

    # Measure FAISS index construction
    start = time.perf_counter()

    store = VectorStore(embeddings.shape[1])

    metadata = [
        {
            "source": item["source"],
            "chunk": item["chunk"],
        }
        for item in DOCUMENTS
    ]

    store.add(embeddings, texts, metadata)

    index_build_ms = (time.perf_counter() - start) * 1000

    query_results = []
    csv_rows = []
    precision_scores = []
    recall_scores = []
    reciprocal_rank_inputs = []
    answerability_scores = []
    answerability_labels = []

    for query_number, item in enumerate(dataset, start=1):
        query = item["query"]
        relevant = set(item["relevant"])
        expected_answerable = bool(item["expected_answerable"])

        # Query embedding latency
        start = time.perf_counter()
        query_embedding = embedder.encode_query(query)[0]
        embedding_ms = (time.perf_counter() - start) * 1000

        # FAISS search latency
        start = time.perf_counter()
        results = store.search(query_embedding, top_k=TOP_K)
        search_ms = (time.perf_counter() - start) * 1000

        top_score = float(results[0]["score"]) if results else 0.0
        answerability_scores.append(top_score)
        answerability_labels.append(expected_answerable)

        retrieved = [
            f'{result["source"]}::{result["chunk"]}'
            for result in results
        ]

        precision = precision_at_k(retrieved, relevant, TOP_K)
        recall = recall_at_k(retrieved, relevant, TOP_K)

        precision_scores.append(precision)
        recall_scores.append(recall)
        reciprocal_rank_inputs.append((retrieved, relevant))

        ranked_results = []

        for rank, result in enumerate(results, start=1):
            identifier = chunk_id(result)
            is_relevant = identifier in relevant

            ranked_item = {
                "rank": rank,
                "chunk_id": identifier,
                "source": result["source"],
                "chunk": result["chunk"],
                "similarity_score": result["score"],
                "labelled_relevant": is_relevant,
            }

            ranked_results.append(ranked_item)

            csv_rows.append({
                "query_number": query_number,
                "query": query,
                "expected_relevant": ";".join(sorted(relevant)),
                "rank": rank,
                "chunk_id": identifier,
                "source": result["source"],
                "chunk": result["chunk"],
                "similarity_score": result["score"],
                "labelled_relevant": is_relevant,
                "embedding_ms": round(embedding_ms, 3),
                "search_ms": round(search_ms, 3),
            })

        query_results.append({
            "query_number": query_number,
            "query": query,
            "expected_relevant": sorted(relevant),
            "expected_answerable": expected_answerable,
            "top_similarity_score": top_score,
            "retrieved": ranked_results,
            "precision_at_k": precision,
            "recall_at_k": recall,
            "embedding_ms": round(embedding_ms, 3),
            "faiss_search_ms": round(search_ms, 3),
            "total_query_ms": round(embedding_ms + search_ms, 3),
        })

        print(f"\n[{query_number}/{len(dataset)}] {query}")
        print(
            f"Embedding: {embedding_ms:.2f} ms | "
            f"FAISS: {search_ms:.2f} ms"
        )

        for result in ranked_results:
            status = "RELEVANT" if result["labelled_relevant"] else "UNLABELLED"
            print(
                f'  #{result["rank"]} {result["chunk_id"]} '
                f'| score={result["similarity_score"]:.4f} '
                f'| {status}'
            )

    count = len(dataset)

    mean_precision = sum(precision_scores) / count
    mean_recall = sum(recall_scores) / count
    mrr = mean_reciprocal_rank(reciprocal_rank_inputs)

    threshold_values = [round(value / 100, 2) for value in range(30, 91, 5)]
    threshold_results = [
        answerability_metrics(answerability_scores, answerability_labels, threshold)
        for threshold in threshold_values
    ]
    # Prefer the threshold with highest balanced accuracy; ties prefer fewer false accepts.
    recommended = max(
        threshold_results,
        key=lambda row: (
            (row["recall"] + row["specificity"]) / 2,
            -row["false_positive"],
            row["threshold"],
        ),
    )

    average_embedding_ms = sum(
        item["embedding_ms"] for item in query_results
    ) / count

    average_search_ms = sum(
        item["faiss_search_ms"] for item in query_results
    ) / count

    average_total_ms = sum(
        item["total_query_ms"] for item in query_results
    ) / count

    summary = {
        "project": "LocalMind",
        "report_generated_utc": datetime.now(timezone.utc).isoformat(),
        "benchmark_type": "isolated_synthetic_retrieval",
        "dataset": str(DATASET_PATH.relative_to(ROOT)),
        "queries_evaluated": count,
        "top_k": TOP_K,
        "corpus_chunks": len(DOCUMENTS),
        "answerability_evaluation": {
            "method": "top-1 raw cosine similarity threshold sweep",
            "thresholds": threshold_results,
            "recommended_threshold_on_this_dataset": recommended,
            "warning": (
                "Synthetic six-chunk corpus and manually labelled queries only; "
                "do not treat this threshold as production-calibrated."
            ),
        },
        "metrics": {
            "mean_precision_at_k": mean_precision,
            "mean_recall_at_k": mean_recall,
            "mean_reciprocal_rank": mrr,
        },
        "latency_ms": {
            "model_initialization": round(model_load_ms, 3),
            "corpus_embedding": round(corpus_embedding_ms, 3),
            "index_construction": round(index_build_ms, 3),
            "average_query_embedding": round(average_embedding_ms, 3),
            "average_faiss_search": round(average_search_ms, 3),
            "average_total_query": round(average_total_ms, 3),
        },
        "queries": query_results,
        "score_note": (
            "Similarity scores are raw FAISS inner-product scores "
            "from normalized embeddings, not probabilities."
        ),
        "relevance_note": (
            "Relevance is based only on the supplied dataset labels. "
            "Unlabelled results are not necessarily irrelevant."
        ),
    }

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    json_path = REPORT_DIR / "retrieval_benchmark_latest.json"
    csv_path = REPORT_DIR / "retrieval_benchmark_latest.csv"

    json_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    csv_fields = [
        "query_number",
        "query",
        "expected_relevant",
        "rank",
        "chunk_id",
        "source",
        "chunk",
        "similarity_score",
        "labelled_relevant",
        "embedding_ms",
        "search_ms",
    ]

    with csv_path.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as file:
        writer = csv.DictWriter(file, fieldnames=csv_fields)
        writer.writeheader()
        writer.writerows(csv_rows)

    print("\n" + "=" * 65)
    print("AGGREGATE RETRIEVAL RESULTS")
    print("=" * 65)
    print(f"Queries: {count}")
    print(f"Mean Precision@{TOP_K}: {mean_precision:.3f}")
    print(f"Mean Recall@{TOP_K}: {mean_recall:.3f}")
    print(f"MRR: {mrr:.3f}")
    print("\nANSWERABILITY THRESHOLD SWEEP")
    for row in threshold_results:
        balanced = (row["recall"] + row["specificity"]) / 2
        print(
            f'threshold={row["threshold"]:.2f} | balanced_accuracy={balanced:.3f} | '
            f'false_accept={row["false_acceptance_rate"]:.3f} | '
            f'false_reject={row["false_rejection_rate"]:.3f}'
        )
    print(f'Dataset candidate threshold: {recommended["threshold"]:.2f}')

    print("\nLATENCY")
    print(f"Model initialization: {model_load_ms:.2f} ms")
    print(f"Corpus embedding: {corpus_embedding_ms:.2f} ms")
    print(f"Index construction: {index_build_ms:.2f} ms")
    print(f"Average query embedding: {average_embedding_ms:.2f} ms")
    print(f"Average FAISS search: {average_search_ms:.2f} ms")
    print(f"Average total query: {average_total_ms:.2f} ms")

    print("\nREPORT FILES")
    print(json_path)
    print(csv_path)
    print("=" * 65)


if __name__ == "__main__":
    main()
