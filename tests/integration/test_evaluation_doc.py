"""Ensure the evaluation report covers the required evidence and error sections."""

from pathlib import Path

REPORT = Path(__file__).resolve().parents[2] / "docs" / "EVALUATION.md"


def test_evaluation_report_has_required_sections_and_cases() -> None:
    content = REPORT.read_text(encoding="utf-8")
    required = (
        "## Setup and configuration",
        "## Retrieval metrics",
        "## Four evidence cases",
        "### 1. Correct chunk retrieved",
        "### 2. Wrong chunk retrieved",
        "### 3. Multiple relevant chunks retrieved",
        "### 4. Insufficient information",
        "## Error analysis",
        "## Excluded metrics and limitations",
        "Incorrect retrieval",
        "Irrelevant chunks",
        "Poor chunk boundaries",
        "Missing context",
        "Hallucinated answers",
        "Ambiguous questions",
        "Duplicate content",
        "Long-context issues",
        "Aggregate answer correctness, generation latency, token usage, and model cost remain",
        "## Targeted live Gemini validation",
        "162 passed, 11 skipped",
    )
    for section in required:
        assert section in content


def test_report_declares_gemini_results_deferred_without_claiming_success() -> None:
    content = REPORT.read_text(encoding="utf-8")
    assert "Gemini generation was deliberately skipped" in content
    assert "The 29-question CSV and summary remain retrieval-only" in content
    assert "no aggregate live answer rate" in content
