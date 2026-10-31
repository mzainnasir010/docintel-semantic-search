"""Two-pass, page-wise cleanup of recurring document headers and footers."""

from __future__ import annotations

import logging
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Callable, Iterable, Iterator

from docintel.models import PageContent
from docintel.preprocessing.cleaning import clean_text

logger = logging.getLogger(__name__)
_PAGE_NUMBER = re.compile(r"^(?:page\s+)?\d+(?:\s+of\s+\d+)?$", re.IGNORECASE)
_PAGE_VARIANT = re.compile(r"\bpage\s+\d+(\s+of\s+\d+)?\b", re.IGNORECASE)


@dataclass
class BoilerplateReport:
    """Counts of normalized recurring lines removed during preprocessing."""

    pages_processed: int = 0
    removed_lines: dict[str, int] = field(default_factory=dict)


def _normalized_candidate(line: str) -> str:
    normalized = re.sub(r"\s+", " ", line.strip()).casefold()
    normalized = _PAGE_VARIANT.sub(
        lambda match: "page # of #" if match.group(1) else "page #", normalized
    )
    return normalized


def _position_lines(text: str) -> tuple[list[str], list[str]]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[:1], lines[-1:]


def iter_preprocessed_pages(
    page_factory: Callable[[], Iterable[PageContent]],
    *,
    report: BoilerplateReport | None = None,
) -> Iterator[PageContent]:
    """Clean pages and strip repeated boilerplate with bounded page memory.

    `page_factory` must return a fresh page iterator each time. The first pass
    counts only candidate boundary lines; the second pass yields cleaned pages
    individually, preserving page metadata and avoiding an in-memory page list.
    """
    result_report = report if report is not None else BoilerplateReport()
    top_counts: Counter[str] = Counter()
    bottom_counts: Counter[str] = Counter()
    representatives: dict[str, str] = {}
    page_count = 0

    for page in page_factory():
        page_count += 1
        top, bottom = _position_lines(page.text)
        for line in top:
            normalized = _normalized_candidate(line)
            top_counts[normalized] += 1
            representatives.setdefault(normalized, line)
        for line in bottom:
            normalized = _normalized_candidate(line)
            bottom_counts[normalized] += 1
            representatives.setdefault(normalized, line)

    if page_count == 0:
        return
    threshold = max(2, math.ceil(page_count * 0.5))
    recurring = {
        candidate
        for candidate, count in (top_counts | bottom_counts).items()
        if count >= threshold
    }
    recurring.update(
        candidate
        for candidate, count in (top_counts | bottom_counts).items()
        if _PAGE_NUMBER.fullmatch(candidate)
    )

    for page in page_factory():
        lines = page.text.splitlines()
        nonempty_indices = [index for index, line in enumerate(lines) if line.strip()]
        boundary_indices = set(nonempty_indices[:1] + nonempty_indices[-1:])
        kept: list[str] = []
        for index, line in enumerate(lines):
            normalized = _normalized_candidate(line)
            is_page_number = bool(_PAGE_NUMBER.fullmatch(normalized))
            if index in boundary_indices and (
                normalized in recurring or is_page_number
            ):
                result_report.removed_lines[normalized] = (
                    result_report.removed_lines.get(normalized, 0) + 1
                )
                continue
            kept.append(line)
        result_report.pages_processed += 1
        yield page.model_copy(update={"text": clean_text("\n".join(kept))})

    if result_report.removed_lines:
        logger.info(
            "Removed recurring document boilerplate from %s pages: %s",
            result_report.pages_processed,
            result_report.removed_lines,
        )
