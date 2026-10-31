"""Run evaluated queries against the real index and render a results table."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROJECT_SRC = PROJECT_ROOT / "backend" / "src"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PROJECT_SRC) not in sys.path:
    sys.path.insert(0, str(PROJECT_SRC))

from quillseek.search import SearchService

QUERY_IDS = [
    "q-002", "q-005", "q-010", "q-016", "q-019", "q-022", "q-025", "q-028"
]
WEAK_QUERY = "How do I configure Kubernetes horizontal pod autoscaling for production?"
TABLE_HEADER = "| Example query | Retrieved document and page | Similarity | Result |"


def _grade(response, expected_doc_name: str | None, expected_pages: list[int]) -> str:
    if expected_doc_name is None:
        return "Weak match"
    if not response.results:
        return "Weak match"
    if (
        response.results[0].doc_name == expected_doc_name
        and response.results[0].page_number in expected_pages
    ):
        return "Correct"
    if any(result.doc_name == expected_doc_name for result in response.results):
        return "Partial"
    return "Weak match"


def generate_search_examples(
    *,
    service=None,
    questions_path: str | Path = PROJECT_ROOT / "eval" / "questions.json",
    output_path: str | Path = PROJECT_ROOT / "docs" / "SEARCH_EXAMPLES.md",
) -> Path:
    """Run eight evaluated questions and one off-topic query, then save Markdown."""
    active_service = service or SearchService()
    questions = json.loads(Path(questions_path).read_text(encoding="utf-8"))
    questions_by_id = {question["id"]: question for question in questions}
    examples = [questions_by_id[question_id] for question_id in QUERY_IDS]
    examples.append(
        {
            "question": WEAK_QUERY,
            "expected_doc_name": None,
            "expected_pages": [],
        }
    )

    rows: list[str] = []
    for example in examples:
        response = active_service.search(example["question"], k=5)
        if response.results:
            top = response.results[0]
            retrieved = f"{top.doc_name}, page {top.page_number}"
            similarity = f"{top.similarity:.3f}"
        else:
            retrieved = "No relevant result"
            similarity = "—"
        grade = _grade(
            response,
            example.get("expected_doc_name"),
            example.get("expected_pages", []),
        )
        query = example["question"].replace("|", "\\|")
        rows.append(f"| {query} | {retrieved} | {similarity} | {grade} |")

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    document = "\n".join(
        [
            "# Search examples",
            "",
            "Measured results from the persistent corpus index. Correctness is judged "
            "against the expected source document and page in `eval/questions.json`; "
            "the final query is intentionally off-topic.",
            "",
            TABLE_HEADER,
            "|---|---|---:|---|",
            *rows,
            "",
        ]
    )
    destination.write_text(document, encoding="utf-8")
    return destination


def main() -> int:
    output = generate_search_examples()
    print(f"Wrote measured search results to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
