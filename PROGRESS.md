# PROGRESS

## NEXT STEP
- Step ID and title: Step 0.3 - Corpus assembly
- Exactly what to do next: Propose 2-3 corpus themes and ask the user to choose one. After approval, assemble 5-15 public, legally redistributable documents on that theme, with related but distinct subjects; include PDFs plus at least one DOCX and one TXT. Add `scripts/build_corpus.py` and `data/sample_docs/SOURCES.md` with source URLs and licences. If downloads are blocked, provide manual download links/instructions and wait. Add a test for 5-15 allowed file types and SOURCES.md coverage.
- Files likely to be touched: `scripts/build_corpus.py`, `data/sample_docs/`, `tests/`, `PROGRESS.md`.
- Pending user input or blockers: User must approve one corpus theme before assembly.

## Current state summary
- Step 0.1 scaffold is implemented; Python 3.11.9 is available.
- Package is `docintel`; configuration uses `pydantic-settings` and supports environment overrides.
- Console and rotating file logging are configured by `configure_logging`.
- All requirements in `requirements.txt` are installed in `.venv`; `pip check` reports no broken requirements.
- Gemini `gemini-3.8-flash` is configured and verified with the key in the ignored project-root `.env`; the key is not recorded in Git or progress notes.
- Sentence-transformers model loads with embedding dimension 384; current full test suite: 8 passed, 0 failed.
- GitHub destination was supplied by the user; push is deferred until the project is complete.

## Step log
| Step | Title | Status (done/in-progress/blocked) | Date | Tests (unit/integration) | Notes / files created |
|---|---|---|---|---|---|
| 0.1 | Scaffold the repository | done | 2026-10-31 | 3 unit passed / 0 integration | Initial scaffold, config, logging, pytest config, README, and smoke tests created. Git initialized. Requirements installed; `pip check` clean; runtime imports verified. Commit: `step 0.1: Scaffold the repository`. |
| 0.2 | Gemini API setup | done | 2026-10-31 | 7 unit passed / 1 integration passed | Replaced Ollama with Gemini REST API in PLAN.md and GROUND_TRUTH.md; configured `gemini-3.8-flash`; added safe API check script, request-construction tests, and a live test that reads credentials only from local `.env`. Full `pytest`: 8 passed. Embedding model loaded (384 dimensions). Commit: `step 0.2: Gemini API setup`. |

## Decisions made
- Project name: `docintel` is the temporary package name until Step 8.1 selects the final brand.
- LLM provider: Google Gemini Developer API over HTTPS with `httpx`; model `gemini-3.8-flash` selected and live-verified.
- Embedding model: `sentence-transformers/all-MiniLM-L6-v2` (locked default from PLAN.md).
- Chunk size/overlap and similarity threshold: provisional PLAN.md defaults (800/100/0.25).

## External actions completed by the user
- User supplied hardware: Windows, 16 GB RAM, Intel UHD Graphics 620 integrated GPU. No local LLM installation is required for Gemini.
- User chose Gemini instead of Ollama, created/configured the API key in the ignored project-root `.env`, and confirmed setup. Secret value intentionally not recorded.
- User supplied the GitHub repository URL and authorized pushing the complete project when ready; no push has occurred.

## Blockers / open questions
- Step 0.3 requires user approval of a corpus theme before corpus assembly.

## How to run (kept current)
- Setup: `python -m venv .venv`; `.\\.venv\\Scripts\\Activate.ps1`; `python -m pip install -r requirements.txt`.
- Tests: `.venv\\Scripts\\python.exe -m pytest` (8 passed, including Gemini live integration).
- Gemini check: `.venv\\Scripts\\python.exe scripts/check_gemini.py`.
- Backend: not implemented yet.
- Frontend: not implemented yet.
