"""Check search-example generation writes the required measured-results table."""

import json
from pathlib import Path

from quillseek.models import Chunk, SearchResponse, SearchResult
from scripts.make_search_examples import generate_search_examples


class FakeSearchService:
    def __init__(self, questions):
        self.by_question = {item["question"]: item for item in questions}
        self.calls = []

    def search(self, query, k):
        self.calls.append((query, k))
        expected = self.by_question.get(query)
        if not expected or expected["expected_doc_name"] is None:
            return SearchResponse(results=[], is_relevant=False)
        page = expected["expected_pages"][0]
        result = SearchResult(
            chunk=Chunk(
                chunk_id=f"{expected['id']}-{page}",
                doc_id="expected-doc",
                doc_name=expected["expected_doc_name"],
                text="Evidence-backed result",
                page_number=page,
            ),
            similarity=0.91,
            rank=1,
        )
        return SearchResponse(results=[result], is_relevant=True)


def test_examples_script_writes_nine_rows_with_required_columns(tmp_path) -> None:
    root = Path(__file__).resolve().parents[2]
    question_path = root / "eval" / "questions.json"
    questions = json.loads(question_path.read_text(encoding="utf-8"))
    service = FakeSearchService(questions)
    output = tmp_path / "SEARCH_EXAMPLES.md"

    generated = generate_search_examples(
        service=service, questions_path=question_path, output_path=output
    )
    content = generated.read_text(encoding="utf-8")
    table_lines = [line for line in content.splitlines() if line.startswith("|")]

    assert generated == output
    assert "| Example query | Retrieved document and page | Similarity | Result |" in content
    assert len(table_lines) == 11  # header, separator, and 9 measured query rows
    assert all(len(line.split("|")) == 6 for line in table_lines)
    assert content.count("| Correct |") == 8
    assert content.count("| Weak match |") == 1
    assert len(service.calls) == 9
