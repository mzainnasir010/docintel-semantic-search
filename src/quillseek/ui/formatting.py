"""Safe HTML formatting helpers for search results and RAG answers."""

from __future__ import annotations

import html
from typing import Any


def _text(value: Any, fallback: str = "—") -> str:
    return html.escape(str(value if value not in (None, "") else fallback))


def format_search_results(payload: dict[str, Any]) -> str:
    """Render ranked chunks as readable cards, or a helpful empty state."""
    results = payload.get("results", [])
    if not payload.get("is_relevant") or not results:
        return (
            '<section class="empty-state qs-empty-results"><h3>No matching passage found</h3>'
            "<p>Try another question, or upload and index documents in the Documents tab.</p></section>"
        )
    cards = []
    for item in results:
        chunk = item.get("chunk", {})
        similarity = float(item.get("similarity", 0.0))
        section = chunk.get("section") or "—"
        cards.append(
            '<article class="qs-card result-card">'
            f'<div class="result-heading"><span class="result-rank">#{int(item.get("rank", 0))}</span>'
            f'<span class="score-pill">{similarity:.3f}</span></div>'
            f'<h3>{_text(chunk.get("doc_name"))}</h3>'
            f'<p class="result-location">Page {_text(chunk.get("page_number"))} · Section {_text(section)}</p>'
            f'<div class="result-text">{_text(chunk.get("text"), "No passage text")}</div>'
            "</article>"
        )
    return '<div class="qs-results">' + "".join(cards) + "</div>"


def format_answer(payload: dict[str, Any]) -> str:
    """Render a grounded answer in a visually distinct or refusal-styled card."""
    answer = str(payload.get("answer", ""))
    refused = bool(payload.get("refused"))
    answer_html = _text(answer, "No answer was returned.").replace("\n", "<br>")
    if refused:
        return (
            '<section class="answer-card refused">'
            '<div class="answer-eyebrow">Not found in your documents</div>'
            f"<p>{answer_html}</p></section>"
        )
    return (
        '<section class="answer-card">'
        '<div class="answer-eyebrow">Answer from your documents</div>'
        f"<p>{answer_html}</p></section>"
    )


def format_sources(sources: list[dict[str, Any]]) -> str:
    """Render expandable source cards with page, similarity, and safe snippets."""
    if not sources:
        return '<div class="empty-state qs-empty-sources">No source passages to show.</div>'
    cards = []
    for source in sources:
        label = _text(source.get("label"), "S?")
        similarity = float(source.get("similarity", 0.0))
        snippet = _text(source.get("snippet"), "No excerpt available.").replace("\n", "<br>")
        cards.append(
            '<details class="source-card">'
            f'<summary><span class="source-label">[{label}]</span> '
            f'<strong>{_text(source.get("doc_name"))}</strong> · Page {_text(source.get("page_number"))} '
            f'<span class="score-pill">{similarity:.3f}</span></summary>'
            f'<div class="source-snippet">{snippet}</div></details>'
        )
    return '<div class="qs-sources">' + "".join(cards) + "</div>"
