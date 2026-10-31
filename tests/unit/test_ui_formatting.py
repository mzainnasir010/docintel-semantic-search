"""Formatting tests for inspectable search results, citations, and refusal states."""

from quillseek.ui.formatting import format_answer, format_search_results, format_sources


def test_search_result_card_includes_rank_score_document_page_and_text() -> None:
    card = format_search_results(
        {
            "is_relevant": True,
            "results": [
                {
                    "rank": 1,
                    "similarity": 0.8766,
                    "chunk": {
                        "doc_name": "python_asyncio.txt",
                        "page_number": 2,
                        "section": "Tasks",
                        "text": "Asyncio runs concurrent tasks.",
                    },
                }
            ],
        }
    )
    assert "#1" in card
    assert "0.877" in card
    assert "python_asyncio.txt" in card
    assert "Page 2" in card
    assert "Section Tasks" in card
    assert "Asyncio runs concurrent tasks." in card


def test_source_cards_show_label_document_page_score_and_expandable_snippet() -> None:
    cards = format_sources(
        [
            {
                "label": "S1",
                "doc_name": "python_json.docx",
                "page_number": 1,
                "similarity": 0.75,
                "snippet": "JSON is a data format.",
            }
        ]
    )
    assert "[S1]" in cards
    assert "python_json.docx" in cards
    assert "Page 1" in cards
    assert "0.750" in cards
    assert "<details" in cards
    assert "JSON is a data format." in cards


def test_refusal_answer_has_distinct_not_found_style() -> None:
    card = format_answer(
        {
            "refused": True,
            "answer": "the answer is not present in the supplied documents",
        }
    )
    assert "answer-card refused" in card
    assert "Not found in your documents" in card
    assert "the answer is not present" in card


def test_html_content_is_escaped_and_empty_results_point_to_documents() -> None:
    unsafe = format_search_results(
        {
            "is_relevant": True,
            "results": [
                {
                    "rank": 1,
                    "similarity": 0.8,
                    "chunk": {
                        "doc_name": "<img src=x>",
                        "page_number": 1,
                        "text": "<script>alert(1)</script>",
                    },
                }
            ],
        }
    )
    empty = format_search_results({"is_relevant": False, "results": []})
    assert "&lt;img src=x&gt;" in unsafe
    assert "&lt;script&gt;" in unsafe
    assert "<script>" not in unsafe
    assert "Documents tab" in empty
