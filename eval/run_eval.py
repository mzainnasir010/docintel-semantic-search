"""Run ranked retrieval and grounded-answer evaluation against the local index."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "backend" / "src"
for import_path in (ROOT, SRC):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from quillseek.config import get_settings
from quillseek.rag.llm import GeminiClient
from quillseek.rag.llm import LLMError, RateLimitError
from quillseek.rag.prompt import PromptBuilder
from quillseek.rag.service import CitationValidationError, RAGService
from quillseek.search import SearchService

PRICING_SOURCE = "https://ai.google.dev/gemini-api/docs/pricing"
PRICING_CHECKED = "2026-10-31"
_CITATION = re.compile(r"\[(S[^\]]*)\]")
EVALUATION_K_VALUES = (3, 5, 10, 20)


def pricing_for(model: str, run_date: date) -> tuple[float, float]:
    """Return paid Standard token rates (USD per million) for the configured model."""
    if model in {"gemini-3.6-flash", "gemini-3.8-flash"}:
        if run_date <= date(2026, 12, 31):
            return 0.75, 3.75
        return 1.50, 7.50
    raise ValueError(f"No dated pricing entry for Gemini model {model!r}")


def _read_index_time(path: Path) -> float | None:
    if not path.exists():
        return None
    try:
        records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except (OSError, json.JSONDecodeError):
        return None
    if not records:
        return None
    latest = max(records, key=lambda record: record.get("started_at", ""))
    value = latest.get("elapsed_seconds")
    return float(value) if value is not None else None


def _key_fact_coverage(expected: str, answer: str) -> float:
    from eval.metrics import key_fact_coverage

    return key_fact_coverage(expected, answer)


def _evaluate_one(
    question: dict[str, Any],
    search_service: SearchService,
    rag_service: RAGService,
    *,
    input_rate: float,
    output_rate: float,
    index_seconds: float | None,
    skip_rag: bool = False,
) -> dict[str, Any]:
    from eval.metrics import mean_relevant_similarity, priced_token_cost_usd, retrieval_metrics

    started = time.perf_counter()
    search_results: dict[int, list] = {}
    search_latency: dict[int, float] = {}
    for k in EVALUATION_K_VALUES:
        tick = time.perf_counter()
        search_results[k] = search_service.search(question["question"], k=k).results
        search_latency[k] = (time.perf_counter() - tick) * 1000

    is_answerable = question.get("type") != "unanswerable"
    row: dict[str, Any] = {
        "question_id": question["id"],
        "question": question["question"],
        "question_type": question.get("type", "unknown"),
        "expected_doc_name": question.get("expected_doc_name"),
        "expected_pages": json.dumps(question.get("expected_pages", [])),
        "expected_answer": question.get("expected_answer", ""),
        **{f"retrieval_k{k}_ms": round(search_latency[k], 3) for k in EVALUATION_K_VALUES},
        "indexing_seconds_latest_run": index_seconds,
    }
    retrieved5 = search_results[5]
    for k in EVALUATION_K_VALUES:
        results = search_results[k]
        row[f"retrieved_k{k}"] = json.dumps([
            {"rank": item.rank, "doc_name": item.chunk.doc_name, "page": item.chunk.page_number,
             "similarity": item.similarity, "chunk_id": item.chunk.chunk_id}
            for item in results
        ])
        if is_answerable:
            metrics = retrieval_metrics(
                results,
                expected_doc_name=question["expected_doc_name"],
                expected_pages=question["expected_pages"],
                k=k,
            )
            row.update({
                f"hit_at_{k}": metrics.hit_at_k,
                f"precision_at_{k}": metrics.precision_at_k,
                f"recall_at_{k}": metrics.recall_at_k,
                f"mrr_at_{k}": metrics.mrr,
                f"mean_correct_similarity_at_{k}": mean_relevant_similarity(
                    results, expected_doc_name=question["expected_doc_name"],
                    expected_pages=question["expected_pages"],
                ),
            })
        else:
            row.update({f"hit_at_{k}": None, f"precision_at_{k}": None,
                        f"recall_at_{k}": None, f"mrr_at_{k}": None,
                        f"mean_correct_similarity_at_{k}": None})

    generation_started = time.perf_counter()
    try:
        if skip_rag:
            raise RuntimeError("DeferredGeminiRun: RAG generation was explicitly skipped")
        response = rag_service.ask(question["question"], k=5)
        row["answer"] = response.answer
        row["refused"] = response.refused
        row["retrieval_ms"] = round(response.retrieval_ms, 3)
        row["generation_ms"] = round(response.generation_ms, 3)
        row["input_tokens"] = response.input_tokens
        row["output_tokens"] = response.output_tokens
        row["total_tokens"] = response.total_tokens
        labels = _CITATION.findall(response.answer)
        source_labels = {source.label for source in response.sources}
        retrieved_locations = {
            (item.chunk.doc_name, item.chunk.page_number) for item in response.retrieved_chunks
        }
        source_locations_valid = all(
            (source.doc_name, source.page_number) in retrieved_locations
            for source in response.sources
        )
        row["grounding_valid"] = (
            not labels if response.refused else bool(labels) and set(labels) <= source_labels and source_locations_valid
        )
        row["sources"] = json.dumps([source.model_dump(mode="json") for source in response.sources])
        row["refusal_correct"] = response.refused == (not is_answerable)
        if is_answerable:
            coverage = _key_fact_coverage(question["expected_answer"], response.answer)
            row["key_fact_coverage"] = round(coverage, 4)
            row["answer_correct_proxy"] = coverage >= 0.60 and not response.refused
        else:
            row["key_fact_coverage"] = None
            row["answer_correct_proxy"] = row["refusal_correct"]
    except (LLMError, CitationValidationError, RuntimeError) as error:  # preserve rows on provider/citation failures
        row.update({
            "answer": None,
            "refused": None,
            "retrieval_ms": None,
            "generation_ms": None,
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
            "grounding_valid": None,
            "sources": "[]",
            "refusal_correct": None,
            "key_fact_coverage": None,
            "answer_correct_proxy": None,
            "evaluation_error": str(error) if skip_rag else f"{type(error).__name__}: {error}",
        })
    end_to_end_ms = (time.perf_counter() - started) * 1000
    row["end_to_end_ms"] = round(end_to_end_ms, 3)
    # Use provider usage when available. Otherwise estimate tokens at 4 chars/token;
    # the source field makes this limitation explicit in the raw results.
    input_tokens = row.get("input_tokens")
    output_tokens = row.get("output_tokens")
    usage_source = "gemini_usage_metadata"
    if skip_rag:
        input_tokens, output_tokens = 0, 0
        usage_source = "deferred_gemini_run"
        row["estimated_paid_tier_cost_usd"] = None
        row["token_usage_source"] = usage_source
        return row
    if row.get("refused") is True and row.get("generation_ms") == 0:
        input_tokens, output_tokens = 0, 0
        usage_source = "not_called_threshold_refusal"
    elif input_tokens is None or output_tokens is None:
        prompt = PromptBuilder().build(
            question["question"], retrieved5,
            max_chars=get_settings().rag_prompt_char_budget,
        ).text if retrieved5 else question["question"]
        input_tokens = max(1, (len(prompt) + 3) // 4)
        answer_text = row.get("answer") or ""
        output_tokens = (len(answer_text) + 3) // 4
        usage_source = "estimated_characters_divided_by_4"
    row["token_usage_source"] = usage_source
    row["estimated_paid_tier_cost_usd"] = priced_token_cost_usd(
        int(input_tokens), int(output_tokens), input_per_million=input_rate,
        output_per_million=output_rate,
    )
    return row


def _summarize(rows: list[dict[str, Any]], *, model: str, input_rate: float,
               output_rate: float, index_seconds: float | None) -> dict[str, Any]:
    answerable = [row for row in rows if row["question_type"] != "unanswerable"]
    live_rag_rows = [row for row in rows if row.get("token_usage_source") != "deferred_gemini_run"]
    def average(field: str, subset: list[dict[str, Any]]) -> float | None:
        values = [row[field] for row in subset if isinstance(row.get(field), (int, float))]
        return mean(values) if values else None
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pricing_checked": PRICING_CHECKED,
        "pricing_source": PRICING_SOURCE,
        "pricing_tier": "Gemini Developer API Standard paid-tier list pricing; free-tier eligibility is unknown",
        "model": model,
        "pricing_usd_per_million_tokens": {"input": input_rate, "output_including_thinking": output_rate},
        "question_count": len(rows),
        "answerable_question_count": len(answerable),
        "unanswerable_question_count": len(rows) - len(answerable),
        "rag_deferred_question_count": sum(row.get("token_usage_source") == "deferred_gemini_run" for row in rows),
        "retrieval": {
            str(k): {field: average(f"{field}_at_{k}", answerable)
                     for field in ("hit", "precision", "recall", "mrr")}
            for k in EVALUATION_K_VALUES
        },
        "mean_correct_similarity": {
            str(k): average(f"mean_correct_similarity_at_{k}", answerable) for k in EVALUATION_K_VALUES
        },
        "answer_correct_proxy_rate": average("answer_correct_proxy", rows),
        "grounding_valid_rate": average("grounding_valid", rows),
        "refusal_correct_rate": average("refusal_correct", rows),
        "latency_ms_mean": {field: average(field, rows) for field in
                             ("retrieval_ms", "generation_ms", "end_to_end_ms", *(f"retrieval_k{k}_ms" for k in EVALUATION_K_VALUES))},
        "indexing_seconds_latest_run": index_seconds,
        "token_usage": {
            "input_tokens": sum(row.get("input_tokens") or 0 for row in live_rag_rows),
            "output_tokens": sum(row.get("output_tokens") or 0 for row in live_rag_rows),
            "estimated_paid_tier_cost_usd": (
                sum(row.get("estimated_paid_tier_cost_usd") or 0 for row in live_rag_rows)
                if live_rag_rows else None
            ),
            "sources": sorted({row["token_usage_source"] for row in rows}),
        },
        "excluded_metrics": {
            "BLEU/ROUGE": "not suitable as standalone measures of factual correctness for short grounded answers",
            "LLM_judge": "excluded to avoid adding a second model, cost, and subjective variance; lexical key-fact coverage is a transparent proxy, not a final human correctness judgment",
            "actual_billed_cost": "cannot be established without account tier, discounts, caching, and billing data; reported cost applies published paid-tier token rates",
        },
    }


def run_evaluation(
    questions: list[dict[str, Any]],
    search_service: SearchService,
    rag_service: RAGService,
    *,
    model: str,
    results_path: Path,
    summary_path: Path,
    index_runs_path: Path,
    resume: bool = False,
    skip_rag: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Run all retrieval and answer checks and write CSV plus JSON summary."""
    input_rate, output_rate = pricing_for(model, date.today())
    index_seconds = _read_index_time(index_runs_path)
    previous: dict[str, dict[str, Any]] = {}
    if resume and results_path.exists():
        numeric_fields = {
            *(f"retrieval_k{k}_ms" for k in EVALUATION_K_VALUES), "retrieval_ms", "generation_ms",
            "end_to_end_ms", "input_tokens", "output_tokens", "total_tokens",
            "estimated_paid_tier_cost_usd", "indexing_seconds_latest_run", "hit_at_3",
            "hit_at_5", "precision_at_3", "precision_at_5", "recall_at_3",
            "recall_at_5", "mrr_at_3", "mrr_at_5", "mean_correct_similarity_at_3",
            "mean_correct_similarity_at_5", "hit_at_10", "hit_at_20", "precision_at_10",
            "precision_at_20", "recall_at_10", "recall_at_20", "mrr_at_10", "mrr_at_20",
            "mean_correct_similarity_at_10", "mean_correct_similarity_at_20", "key_fact_coverage",
        }
        bool_fields = {"refused", "grounding_valid", "refusal_correct", "answer_correct_proxy"}
        with results_path.open("r", encoding="utf-8", newline="") as handle:
            for saved in csv.DictReader(handle):
                for field in numeric_fields & saved.keys():
                    value = saved[field]
                    saved[field] = (int(float(value)) if field.endswith("_tokens") else float(value)) if value else None
                for field in bool_fields & saved.keys():
                    value = saved[field]
                    saved[field] = value.casefold() == "true" if value else None
                previous[saved["question_id"]] = saved

    rows: list[dict[str, Any]] = []
    for question in questions:
        cached = previous.get(question["id"])
        if cached is not None and not cached.get("evaluation_error"):
            rows.append(cached)
            continue
        row = _evaluate_one(question, search_service, rag_service,
                            input_rate=input_rate, output_rate=output_rate,
                            index_seconds=index_seconds, skip_rag=skip_rag)
        rows.append(row)
        # One exhausted-quota response is enough; don't spend time issuing more
        # requests that cannot succeed. A later --resume retries this row onward.
        if row.get("evaluation_error", "").startswith("RateLimitError:"):
            break
    results_path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with results_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    summary = _summarize(rows, model=model, input_rate=input_rate,
                         output_rate=output_rate, index_seconds=index_seconds)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return rows, summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", type=Path, default=ROOT / "eval" / "questions.json")
    parser.add_argument("--limit", type=int, help="evaluate only the first N questions (smoke check)")
    parser.add_argument("--resume", action="store_true", help="reuse successful CSV rows and retry incomplete rows")
    parser.add_argument("--skip-rag", action="store_true", help="run real retrieval metrics and mark Gemini answer evaluation deferred")
    parser.add_argument("--results", type=Path, default=ROOT / "eval" / "results" / "results.csv")
    parser.add_argument("--summary", type=Path, default=ROOT / "eval" / "results" / "summary.json")
    args = parser.parse_args()
    questions = json.loads(args.questions.read_text(encoding="utf-8"))
    if args.limit is not None:
        if args.limit < 1:
            parser.error("--limit must be positive")
        questions = questions[:args.limit]
    settings = get_settings()
    search = SearchService()
    rag = RAGService(search_service=search, llm_client=GeminiClient(settings))
    _, summary = run_evaluation(
        questions, search, rag, model=settings.gemini_model,
        results_path=args.results, summary_path=args.summary,
        index_runs_path=ROOT / "eval" / "results" / "index_runs.jsonl",
        resume=args.resume,
        skip_rag=args.skip_rag,
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
