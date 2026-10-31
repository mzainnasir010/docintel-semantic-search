"""Build an attributed corpus from redistributable Python documentation."""

from __future__ import annotations

import textwrap
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

import httpx
import pymupdf as fitz
from docx import Document as WordDocument

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CORPUS_DIR = PROJECT_ROOT / "data" / "sample_docs"
LICENSE_NAME = "Python Software Foundation License Version 2"
LICENSE_URL = "https://docs.python.org/3.12/license.html"
COPYRIGHT_NOTICE = "Copyright © 2001 Python Software Foundation; All Rights Reserved."
CHANGE_NOTICE = (
    "Adaptation note: HTML markup and navigation were removed, whitespace was normalized, "
    "and selected pages were converted to plain text, PDF, or DOCX. "
    "No technical claims were intentionally changed."
)


@dataclass(frozen=True)
class CorpusDocument:
    """One source page and its chosen output format."""

    filename: str
    title: str
    url: str
    output_format: str


DOCUMENTS = (
    CorpusDocument("python_data_structures.txt", "Python Tutorial: Data Structures", "https://docs.python.org/3.12/tutorial/datastructures.html", "txt"),
    CorpusDocument("python_errors_exceptions.txt", "Python Tutorial: Errors and Exceptions", "https://docs.python.org/3.12/tutorial/errors.html", "txt"),
    CorpusDocument("python_modules.txt", "Python Tutorial: Modules", "https://docs.python.org/3.12/tutorial/modules.html", "txt"),
    CorpusDocument("python_input_output.pdf", "Python Tutorial: Input and Output", "https://docs.python.org/3.12/tutorial/inputoutput.html", "pdf"),
    CorpusDocument("python_argparse.pdf", "Python Library: argparse", "https://docs.python.org/3.12/library/argparse.html", "pdf"),
    CorpusDocument("python_pathlib.docx", "Python Library: pathlib", "https://docs.python.org/3.12/library/pathlib.html", "docx"),
    CorpusDocument("python_asyncio.txt", "Python Library: asyncio", "https://docs.python.org/3.12/library/asyncio.html", "txt"),
    CorpusDocument("python_logging.pdf", "Python Library: logging", "https://docs.python.org/3.12/library/logging.html", "pdf"),
    CorpusDocument("python_json.docx", "Python Library: json", "https://docs.python.org/3.12/library/json.html", "docx"),
)


class _DocsTextParser(HTMLParser):
    """Extract readable text while omitting navigation and executable markup."""

    _ignored_tags = {"script", "style", "nav", "header", "footer", "noscript"}
    _block_tags = {
        "article", "blockquote", "br", "dd", "div", "dl", "dt", "h1", "h2",
        "h3", "h4", "h5", "h6", "li", "ol", "p", "pre", "section", "table",
        "td", "th", "tr", "ul",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._ignored_depth = 0
        self._parts: list[str] = []
        self._tag_stack: list[tuple[str, bool]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = dict(attrs)
        classes = set((attr_map.get("class") or "").split())
        ignore_element = (
            tag in self._ignored_tags
            or attr_map.get("role") == "navigation"
            or bool(classes & {"related", "sphinxsidebar", "headerlink"})
        )
        self._tag_stack.append((tag, ignore_element))
        if ignore_element:
            self._ignored_depth += 1
        elif not self._ignored_depth and tag in self._block_tags:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        matching_index = next(
            (index for index in range(len(self._tag_stack) - 1, -1, -1)
             if self._tag_stack[index][0] == tag),
            None,
        )
        popped: list[tuple[str, bool]] = []
        if matching_index is not None:
            popped = self._tag_stack[matching_index:]
            del self._tag_stack[matching_index:]
        for _, was_ignored in popped:
            if was_ignored:
                self._ignored_depth = max(0, self._ignored_depth - 1)
        if not self._ignored_depth and tag in self._block_tags:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth:
            self._parts.append(data)

    def get_text(self) -> str:
        """Return normalized page text with paragraph boundaries preserved."""
        raw_text = "".join(self._parts)
        paragraphs = [" ".join(line.split()) for line in raw_text.splitlines()]
        return "\n\n".join(line for line in paragraphs if line)


def html_to_text(html: str) -> str:
    """Convert one documentation HTML page to readable text."""
    parser = _DocsTextParser()
    parser.feed(html)
    return parser.get_text()


def fetch_page(url: str, client: httpx.Client | None = None) -> str:
    """Fetch a page from the official Python documentation site."""
    if client is not None:
        response = client.get(url)
    else:
        response = httpx.get(url, timeout=30.0, follow_redirects=True)
    response.raise_for_status()
    return response.text


def _attribution(document: CorpusDocument) -> str:
    return "\n\n".join(
        (
            document.title,
            f"Source: {document.url}",
            f"License: {LICENSE_NAME} ({LICENSE_URL})",
            COPYRIGHT_NOTICE,
            CHANGE_NOTICE,
        )
    )


def _write_pdf(path: Path, title: str, text: str) -> None:
    pdf = fitz.open()
    pdf.set_metadata({"title": title, "author": "Python Software Foundation"})
    page = pdf.new_page()
    y = 52
    for paragraph in text.splitlines():
        for line in textwrap.wrap(paragraph, width=88) or [""]:
            if y > 785:
                page = pdf.new_page()
                y = 52
            page.insert_text((50, y), line, fontsize=9, fontname="helv")
            y += 13
        y += 4
    pdf.save(path)
    pdf.close()


def _write_docx(path: Path, title: str, text: str) -> None:
    word_document = WordDocument()
    word_document.add_heading(title, level=1)
    for paragraph in text.splitlines():
        if paragraph.strip():
            word_document.add_paragraph(paragraph)
    word_document.save(path)


def _write_license(path: Path) -> None:
    """Retain the source license and copyright notice beside the corpus."""
    license_text = """PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2

Copyright © 2001 Python Software Foundation; All Rights Reserved.

1. This LICENSE AGREEMENT is between the Python Software Foundation ("PSF"), and the Individual or Organization ("Licensee") accessing and otherwise using this software ("Python") in source or binary form and its associated documentation.

2. Subject to the terms and conditions of this License Agreement, PSF hereby grants Licensee a nonexclusive, royalty-free, world-wide license to reproduce, analyze, test, perform and/or display publicly, prepare derivative works, distribute, and otherwise use Python alone or in any derivative version, provided, however, that PSF's License Agreement and PSF's notice of copyright, i.e., "Copyright © 2001 Python Software Foundation; All Rights Reserved" are retained in Python alone or in any derivative version prepared by Licensee.

3. In the event Licensee prepares a derivative work that is based on or incorporates Python or any part thereof, and wants to make the derivative work available to others as provided herein, then Licensee hereby agrees to include in any such work a brief summary of the changes made to Python.

4. PSF is making Python available to Licensee on an "AS IS" basis. PSF MAKES NO REPRESENTATIONS OR WARRANTIES, EXPRESS OR IMPLIED. BY WAY OF EXAMPLE, BUT NOT LIMITATION, PSF MAKES NO AND DISCLAIMS ANY REPRESENTATION OR WARRANTY OF MERCHANTABILITY OR FITNESS FOR ANY PARTICULAR PURPOSE OR THAT THE USE OF PYTHON WILL NOT INFRINGE ANY THIRD PARTY RIGHTS.

5. PSF SHALL NOT BE LIABLE TO LICENSEE OR ANY OTHER USERS OF PYTHON FOR ANY INCIDENTAL, SPECIAL, OR CONSEQUENTIAL DAMAGES OR LOSS AS A RESULT OF MODIFYING, DISTRIBUTING, OR OTHERWISE USING PYTHON, OR ANY DERIVATIVE THEREOF, EVEN IF ADVISED OF THE POSSIBILITY THEREOF.

6. This License Agreement will automatically terminate upon a material breach of its terms and conditions.

7. Nothing in this License Agreement shall be deemed to create any relationship of agency, partnership, or joint venture between PSF and Licensee. This License Agreement does not grant permission to use PSF trademarks or trade name in a trademark sense to endorse or promote products or services of Licensee, or any third party.

8. By copying, installing or otherwise using Python, Licensee agrees to be bound by the terms and conditions of this License Agreement.

Official source: https://docs.python.org/3.12/license.html
"""
    path.write_text(license_text, encoding="utf-8")


def build_corpus(output_dir: Path = CORPUS_DIR) -> list[Path]:
    """Download, normalize, and convert the selected licensed documentation pages."""
    output_dir.mkdir(parents=True, exist_ok=True)
    created_paths: list[Path] = []
    rows = [
        "# Sample Corpus Sources", "",
        "Theme: Python language and standard-library technical documentation.", "",
        f"All pages are licensed under the {LICENSE_NAME}.",
        "The license and copyright notice are included in `PSF_LICENSE.txt` and each corpus file.",
        "HTML navigation was removed, whitespace normalized, and selected pages converted to PDF/DOCX/TXT.",
        "No technical claims were intentionally changed.", "",
        "| File | Subject | Source URL | Licence |", "|---|---|---|---|",
    ]
    for source in DOCUMENTS:
        text = f"{_attribution(source)}\n\n{html_to_text(fetch_page(source.url))}"
        destination = output_dir / source.filename
        if source.output_format == "pdf":
            _write_pdf(destination, source.title, text)
        elif source.output_format == "docx":
            _write_docx(destination, source.title, text)
        else:
            destination.write_text(text + "\n", encoding="utf-8")
        created_paths.append(destination)
        rows.append(
            f"| `{source.filename}` | {source.title} | [{source.url}]({source.url}) | "
            f"[{LICENSE_NAME}]({LICENSE_URL}) |"
        )
    _write_license(output_dir / "PSF_LICENSE.txt")
    (output_dir / "SOURCES.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
    return created_paths


def main() -> None:
    """Build the corpus and report the number of documents written."""
    created = build_corpus()
    print(f"Built {len(created)} licensed sample documents in {CORPUS_DIR}")


if __name__ == "__main__":
    main()
