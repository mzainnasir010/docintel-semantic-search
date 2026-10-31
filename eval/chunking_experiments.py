"""Evaluate chunk size, overlap, and strategy against the question set."""

from __future__ import annotations

import csv
import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Sequence

import chromadb

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_SRC = PROJECT_ROOT / "src"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PROJECT_SRC) not in sys.path:
    sys.path.insert(0, str(PROJECT_SRC))

from docintel.chunking import chunk_pages
from docintel.embeddings import Embedder
from docintel.ingestion import ingest_files
from docintel.vectorstore import ChromaVectorStore
from eval.metrics import RetrievalMetrics, mean_metrics, retrieval_metrics
from scripts.build_corpus import CORPUS_DIR, DOCUMENTS

QUESTIONS_PATH = PROJECT_ROOT / "eval" / "questions.json"
CSV_PATH = PROJECT_ROOT / "eval" / "results" / "chunking.csv"
REPORT_PATH = PROJECT_ROOT / "docs" / "CHUNKING_EXPERIMENTS.md"
METRIC_K = 5


@dataclass(frozen=True)
class ExperimentConfig:
    """One chunking configuration to measure."""

    strategy: str
    chunk_size: int
    chunk_overlap: int

    @property
    def name(self) -> str:
        return f"{self.strategy}-{self.chunk_size}-{self.chunk_overlap}"


DEFAULT_CONFIGS = [
    ExperimentConfig(strategy, size, overlap)
    for strategy in ("recursive", "sentence", "section")
    for size in (300, 800, 1500)
    for overlap in (0, 120)
]


def _write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "strategy", "chunk_size", "chunk_overlap", "chunk_count",
        "average_chunk_length", "hit_at_5", "precision_at_5", "recall_at_5",
        "mrr", "index_seconds", "query_seconds", "answerable_questions",
        "missed_questions",
    ]
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def _selection_key(row: dict) -> tuple[float, float, float, float, int]:
    return (
        float(row["mrr"]),
        float(row["recall_at_5"]),
        float(row["hit_at_5"]),
        float(row["precision_at_5"]),
        -int(row["chunk_count"]),
    )


def _write_report(rows: list[dict], selected: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Chunking experiments",
        "",
        f"Evaluated {len(rows)} configurations using {rows[0]['answerable_questions']} answerable "
        "evaluation questions and top-5 retrieval. Hit, precision, recall, and MRR use "
        "the expected document and page(s); mean chunk length and count are measured from "
        "the indexed corpus.",
        "",
        "| Strategy | Size | Overlap | Chunks | Avg. chars | Hit@5 | Precision@5 | Recall@5 | MRR |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['strategy']} | {row['chunk_size']} | {row['chunk_overlap']} | "
            f"{row['chunk_count']} | {row['average_chunk_length']:.1f} | "
            f"{row['hit_at_5']:.3f} | {row['precision_at_5']:.3f} | "
            f"{row['recall_at_5']:.3f} | {row['mrr']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Selected configuration",
            "",
            f"**{selected['strategy']}**, chunk size **{selected['chunk_size']}**, "
            f"overlap **{selected['chunk_overlap']}**. The selection maximizes MRR, "
            "then recall, hit rate, and precision; ties prefer fewer chunks.",
            "",
            "## Observed misses and trade-offs",
            "",
        ]
    )
    for row in rows:
        if row is selected:
            continue
        details = row["missed_questions"] or "No expected document/page was missed at K=5."
        lines.append(
            f"- `{row['strategy']}`, size {row['chunk_size']}, overlap {row['chunk_overlap']}: "
            f"Hit@5 {row['hit_at_5']:.3f}, MRR {row['mrr']:.3f}, "
            f"{row['chunk_count']} chunks averaging {row['average_chunk_length']:.1f} chars. "
            f"Observed misses: {details}"
        )
    lines.extend(
        [
            "",
            "The miss descriptions name the actual expected and retrieved document/page "
            "for each failed top-5 match; they are evidence for the observed trade-offs, "
            "rather than assumptions based only on configured chunk size.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def run_experiments(
    *,
    configurations: Sequence[ExperimentConfig] | None = None,
    corpus_paths: Sequence[str | Path] | None = None,
    questions: list[dict] | None = None,
    questions_path: str | Path = QUESTIONS_PATH,
    output_csv: str | Path = CSV_PATH,
    report_path: str | Path = REPORT_PATH,
    embedder=None,
    client_factory: Callable = chromadb.EphemeralClient,
) -> list[dict]:
    """Re-index in isolated temporary collections and score answerable questions."""
    configs = list(configurations or DEFAULT_CONFIGS)
    input_paths = list(corpus_paths or [CORPUS_DIR / item.filename for item in DOCUMENTS])
    question_items = questions or json.loads(Path(questions_path).read_text(encoding="utf-8"))
    answerable = [item for item in question_items if item["type"] != "unanswerable"]
    if not configs:
        raise ValueError("at least one experiment configuration is required")
    if not answerable:
        raise ValueError("at least one answerable evaluation question is required")

    ingestion = ingest_files(input_paths)
    if ingestion.failed:
        reasons = "; ".join(f"{item.doc_name}: {item.error_message}" for item in ingestion.failed)
        raise RuntimeError(f"Corpus ingestion failed before experiments: {reasons}")
    pages = ingestion.pages
    active_embedder = embedder or Embedder()
    query_vectors = active_embedder.embed_documents([item["question"] for item in answerable])
    rows: list[dict] = []

    for experiment_index, config in enumerate(configs, start=1):
        index_started = time.perf_counter()
        chunks = chunk_pages(
            pages,
            strategy=config.strategy,
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
        )
        vectors = active_embedder.embed_documents([chunk.text for chunk in chunks])
        index_seconds = time.perf_counter() - index_started
        client = client_factory()
        store = ChromaVectorStore(
            collection_name="chunking-experiment",
            embedding_model_name=active_embedder.model_name,
            client=client,
        )
        store.add_chunks(chunks, vectors)

        observations: list[RetrievalMetrics] = []
        missed: list[str] = []
        query_started = time.perf_counter()
        for item, query_vector in zip(answerable, query_vectors):
            results = store.query(query_vector, k=METRIC_K)
            metrics = retrieval_metrics(
                results,
                expected_doc_name=item["expected_doc_name"],
                expected_pages=item["expected_pages"],
                k=METRIC_K,
            )
            observations.append(metrics)
            if not metrics.hit_at_k:
                if results:
                    top = results[0]
                    actual = f"{top.doc_name} p.{top.page_number}"
                else:
                    actual = "no result"
                expected = f"{item['expected_doc_name']} p.{','.join(map(str, item['expected_pages']))}"
                missed.append(f"{item['id']} expected {expected}, got {actual}")
        query_seconds = time.perf_counter() - query_started
        mean = mean_metrics(observations)
        row = {
            "strategy": config.strategy,
            "chunk_size": config.chunk_size,
            "chunk_overlap": config.chunk_overlap,
            "chunk_count": len(chunks),
            "average_chunk_length": (
                sum(len(chunk.text) for chunk in chunks) / len(chunks) if chunks else 0.0
            ),
            "hit_at_5": mean.hit_at_k,
            "precision_at_5": mean.precision_at_k,
            "recall_at_5": mean.recall_at_k,
            "mrr": mean.mrr,
            "index_seconds": index_seconds,
            "query_seconds": query_seconds,
            "missed_questions": "; ".join(missed),
            "answerable_questions": len(answerable),
        }
        rows.append(row)
        print(
            f"[{experiment_index}/{len(configs)}] {config.name}: "
            f"Hit@5={mean.hit_at_k:.3f} MRR={mean.mrr:.3f} chunks={len(chunks)}",
            flush=True,
        )
        client.delete_collection("chunking-experiment")
        del store, client

    selected = max(rows, key=_selection_key)
    _write_csv(rows, Path(output_csv))
    _write_report(rows, selected, Path(report_path))
    return rows


def main() -> int:
    run_experiments()
    print(f"Raw experiment rows: {CSV_PATH}")
    print(f"Experiment report: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
