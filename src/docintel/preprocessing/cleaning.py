"""Repeatable, structure-aware text cleanup for document retrieval.

Text casing is deliberately preserved because capitalization can distinguish
names and technical terms in embedding inputs. Headings, list items, and table
rows retain their own lines while wrapped prose is joined within paragraphs.
"""

from __future__ import annotations

import re
import unicodedata

_PUNCTUATION = str.maketrans(
    {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
        "\u2026": "...",
    }
)
_LIST_LINE = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+|\[[ xX]\]\s+)")
_HEADING_LINE = re.compile(r"^\s{0,3}(?:#{1,6}\s+\S|.+\n?[-=]{3,}\s*$)")
_TABLE_LINE = re.compile(r"\||\t")
_HYPHENATED_LINEBREAK = re.compile(r"(?<=\w)-[ \t]*\r?\n[ \t]*(?=\w)")


def normalize_unicode(text: str) -> str:
    """Apply compatibility normalization so equivalent glyphs compare alike."""
    return unicodedata.normalize("NFKC", text)


def standardize_punctuation(text: str) -> str:
    """Use consistent ASCII quote, dash, and ellipsis forms."""
    return text.translate(_PUNCTUATION)


def remove_control_characters(text: str) -> str:
    """Drop control and invisible format characters while keeping line layout."""
    return "".join(
        char
        for char in text
        if char in "\n\r\t" or unicodedata.category(char) not in {"Cc", "Cf"}
    )


def fix_hyphenation(text: str) -> str:
    """Rejoin words split by a hyphen at a line ending."""
    return _HYPHENATED_LINEBREAK.sub("", text)


def _is_structural_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    return bool(
        _LIST_LINE.match(stripped)
        or _HEADING_LINE.match(stripped)
        or _TABLE_LINE.search(stripped)
    )


def join_wrapped_lines(text: str) -> str:
    """Join wrapped prose lines without merging headings, lists, or table rows."""
    paragraphs = re.split(r"\r?\n[ \t]*\r?\n+", text.strip("\r\n "))
    cleaned_paragraphs: list[str] = []
    for paragraph in paragraphs:
        lines = [line.strip() for line in paragraph.splitlines() if line.strip()]
        if not lines:
            continue
        output: list[str] = []
        prose: list[str] = []

        def flush_prose() -> None:
            if prose:
                output.append(" ".join(prose))
                prose.clear()

        previous_structural = False
        previous_heading = False
        for line in lines:
            structural = _is_structural_line(line)
            heading = bool(_HEADING_LINE.match(line))
            if structural:
                flush_prose()
                output.append(line)
            elif previous_structural:
                if previous_heading:
                    prose.append(line)
                else:
                    flush_prose()
                    output.append(line)
            else:
                prose.append(line)
            previous_structural = structural
            previous_heading = heading
        flush_prose()
        cleaned_paragraphs.append("\n".join(output))
    return "\n\n".join(cleaned_paragraphs)


def collapse_whitespace(text: str) -> str:
    """Trim lines, collapse repeated horizontal spacing, and limit blank lines."""
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    result: list[str] = []
    blank_count = 0
    for line in lines:
        if not line:
            blank_count += 1
            if result and blank_count == 1:
                result.append("")
        else:
            blank_count = 0
            result.append(line)
    return "\n".join(result).strip()


def clean_text(text: str) -> str:
    """Normalize and clean extracted text while retaining document structure."""
    if not text:
        return ""
    text = normalize_unicode(text)
    text = standardize_punctuation(text)
    text = remove_control_characters(text)
    text = fix_hyphenation(text)
    text = join_wrapped_lines(text)
    return collapse_whitespace(text)
