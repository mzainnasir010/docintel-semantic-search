"""Search the configured persistent document index from a terminal."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_SRC = PROJECT_ROOT / "src"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PROJECT_SRC) not in sys.path:
    sys.path.insert(0, str(PROJECT_SRC))

from docintel.search import SearchService


def main() -> int:
    parser = argparse.ArgumentParser(description="Search indexed technical documents.")
    parser.add_argument("query", help="Natural-language question or search phrase")
    parser.add_argument("-k", type=int, default=None, help="Maximum number of results")
    parser.add_argument("--doc-id", help="Restrict results to one stable document ID")
    args = parser.parse_args()

    response = SearchService().search(args.query, k=args.k, doc_filter=args.doc_id)
    if not response.is_relevant:
        print("No relevant results found.")
        return 0
    for result in response.results:
        print(
            f"[{result.rank}] similarity={result.similarity:.3f} "
            f"document={result.doc_name} page={result.page_number} "
            f"section={result.section or '-'} chunk={result.chunk_id}\n"
            f"{result.text}\n"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
