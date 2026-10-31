"""Index the checked-in sample corpus into the configured Chroma collection."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_SRC = PROJECT_ROOT / "src"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PROJECT_SRC) not in sys.path:
    sys.path.insert(0, str(PROJECT_SRC))

from docintel.indexing import index_files
from scripts.build_corpus import CORPUS_DIR, DOCUMENTS


def main() -> int:
    """Run indexing and print compact progress and summary output."""
    paths = [CORPUS_DIR / document.filename for document in DOCUMENTS]

    def show_progress(progress) -> None:
        print(
            f"{progress.percent:6.1f}% {progress.stage:<18} {progress.current_file} "
            f"(indexed={progress.indexed}, skipped={progress.skipped}, "
            f"failed={progress.failed}, chunks={progress.chunks_indexed})"
        )

    summary = index_files(paths, progress_callback=show_progress)
    print(json.dumps(summary.model_dump(mode="json"), indent=2))
    return 1 if summary.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
