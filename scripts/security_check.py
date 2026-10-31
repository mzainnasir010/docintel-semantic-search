"""Check tracked files and Git history for accidental API-key exposure."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECRET_PATTERNS = (
    re.compile(rb"AIza[0-9A-Za-z_-]{30,}"),
    re.compile(rb"GEMINI_API_KEY\s*=\s*[A-Za-z0-9_-]{24,}"),
)


def _git(root: Path, *arguments: str) -> bytes:
    completed = subprocess.run(
        ["git", *arguments], cwd=root, check=True, capture_output=True
    )
    return completed.stdout


def audit_repository(root: Path = ROOT, *, scan_history: bool = True) -> list[str]:
    """Return safe-to-print findings without including any matched secret text."""
    errors: list[str] = []
    tracked = {
        entry.decode("utf-8", errors="replace")
        for entry in _git(root, "ls-files", "-z").split(b"\0")
        if entry
    }
    if ".env" in tracked:
        errors.append("The project-root .env file is tracked by Git.")
    ignored = subprocess.run(
        ["git", "check-ignore", "-q", ".env"], cwd=root, capture_output=True
    )
    if ignored.returncode != 0:
        errors.append("The project-root .env file is not ignored by Git.")

    example_path = root / ".env.example"
    if example_path.is_file():
        for number, line in enumerate(example_path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            name, separator, value = line.partition("=")
            expected = "your-api-key-here" if name == "GEMINI_API_KEY" else ""
            if not separator or value != expected:
                errors.append(f".env.example has an unexpected value at line {number}.")
    else:
        errors.append(".env.example is missing.")

    for relative in sorted(tracked):
        path = root / relative
        if relative == ".env" or not path.is_file():
            continue
        try:
            content = path.read_bytes()
        except OSError:
            errors.append(f"Could not read tracked file {relative}.")
            continue
        if any(pattern.search(content) for pattern in SECRET_PATTERNS):
            errors.append(f"An obvious API-key pattern appears in tracked file {relative}.")

    sample_docs = [
        path for path in tracked
        if path.startswith("data/sample_docs/")
        and Path(path).name not in {"SOURCES.md", "LICENSE"}
    ]
    sources_path = root / "data" / "sample_docs" / "SOURCES.md"
    if not sources_path.is_file():
        errors.append("The sample-document source manifest is missing.")
    else:
        source_manifest = sources_path.read_text(encoding="utf-8")
        missing = [Path(path).name for path in sample_docs if Path(path).name not in source_manifest]
        if missing:
            errors.append("Sample documents are missing from SOURCES.md: " + ", ".join(missing))

    if scan_history:
        commits = _git(root, "rev-list", "--all").decode("ascii").splitlines()
        for commit in commits:
            for pattern in (rb"AIza[0-9A-Za-z_-]{30,}", rb"GEMINI_API_KEY\s*=\s*[A-Za-z0-9_-]{24,}"):
                matches = subprocess.run(
                    ["git", "grep", "-I", "-l", "-E", pattern.decode("ascii"), commit, "--"],
                    cwd=root,
                    capture_output=True,
                )
                if matches.returncode == 0 and matches.stdout.strip():
                    paths = sorted({line.decode("utf-8", errors="replace").split(":", 1)[-1]
                                    for line in matches.stdout.splitlines()})
                    errors.append(
                        f"An obvious API-key pattern appears in Git history ({commit[:8]}): "
                        + ", ".join(paths)
                    )
                    break
    return errors


def main() -> int:
    findings = audit_repository()
    if findings:
        print("Security audit found issues:")
        for finding in findings:
            print(f"- {finding}")
        return 1
    print("Security audit passed: .env is ignored and untracked; no obvious API-key patterns "
          "were found in tracked files or Git history; sample documents have source-manifest entries.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
