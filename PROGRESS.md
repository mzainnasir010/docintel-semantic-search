# PROGRESS

- Step ID and title: Step 1.2 - Router, multi-document ingestion, error boundaries, stable IDs
- Exactly what to do next: Implement an ingestion service that detects file type by extension and content signature and routes to the matching loader. Return clear failed records for unsupported types instead of aborting a batch. Generate stable document IDs as short SHA-256 hashes of file content, process each input independently, record failure reasons and page counts, and continue after failures. Add unit tests for routing, stable IDs, and unsupported types, plus integration coverage for a mixed batch with valid files, a corrupt PDF, and an unsupported file. Keep large-file processing page-iterative where possible.
- Files likely to be touched: `src/docintel/ingestion/`, `src/docintel/models.py`, `tests/unit/`, `tests/integration/`.
- Pending user input or blockers: None.

## Current state summary
- Step 0.1 scaffold is implemented; Python 3.11.9 is available.
- Package is `docintel`; configuration uses `pydantic-settings` and supports environment overrides.
- Console and rotating file logging are configured by `configure_logging`.
- All requirements in `requirements.txt` are installed in `.venv`; `pip check` reports no broken requirements.
- Gemini `gemini-3.8-flash` is configured and live-verified using the ignored project-root `.env`; the key is not recorded in Git or progress notes.
- Sentence-transformers model loads with embedding dimension 384.
- Corpus: 9 redistributable Python docs (4 TXT, 3 PDF, 2 DOCX), each attributed; `SOURCES.md` and PSF license included.
- Current backend regression suite: 22 passed, 0 failed, 1 live Gemini test deselected (`pytest -m "not gemini"`).
- GitHub destination was supplied by the user; push is deferred until the project is complete.

## Step log
| Step | Title | Status (done/in-progress/blocked) | Date | Tests (unit/integration) | Notes / files created |
|---|---|---|---|---|---|
| 0.1 | Scaffold the repository | done | 2026-10-31 | 3 unit passed / 0 integration | Initial scaffold, config, logging, pytest config, README, and smoke tests created. Git initialized. Requirements installed; `pip check` clean; runtime imports verified. Commit: `step 0.1: Scaffold the repository`. |
| 0.2 | Gemini API setup | done | 2026-10-31 | 7 unit passed / 1 integration passed | Replaced Ollama with Gemini REST API in PLAN.md and GROUND_TRUTH.md; configured `gemini-3.8-flash`; added safe API check script, request-construction tests, and a live test that reads credentials only from local `.env`. Full `pytest`: 8 passed. Embedding model loaded (384 dimensions). Commit: `step 0.2: Gemini API setup`. |
| 0.3 | Corpus assembly | done | 2026-10-31 | 1 unit passed / 3 integration passed | Selected Python technical documentation at the user's direction to choose autonomously. Built 9 documents (4 TXT, 3 PDF, 2 DOCX) from official Python 3.12 docs under PSF License Version 2; retained license/copyright and adaptation note. `SOURCES.md` records each URL/licence. `.gitignore` excludes history-named files/folders. Commit: `step 0.3: Corpus assembly`. |
| 1.1 | Data models and loaders | done | 2026-10-31 | 18 unit passed / 4 integration passed | Added validated shared models, resilient PyMuPDF/DOCX/TXT loaders, PDF date parsing, logical DOCX sections and flattened tables, encoding fallbacks, and generated fixtures. `pytest -m "not gemini"`: 22 passed, 1 deselected. Commit: `step 1.1: Data models and loaders`. |

## Decisions made
- Project name: `docintel` is the temporary package name until Step 8.1 selects the final brand.
- LLM provider: Google Gemini Developer API over HTTPS with `httpx`; model `gemini-3.8-flash` selected and live-verified.
- Embedding model: `sentence-transformers/all-MiniLM-L6-v2` (locked default from PLAN.md).
- Chunk size/overlap and similarity threshold: provisional PLAN.md defaults (800/100/0.25).
- Corpus theme: Python language and standard-library documentation; 9 files under PSF License Version 2, selected autonomously after user direction.

## External actions completed by the user
- User supplied hardware: Windows, 16 GB RAM, Intel UHD Graphics 620 integrated GPU. No local LLM installation is required for Gemini.
- User chose Gemini instead of Ollama, created/configured the API key in the ignored project-root `.env`, and confirmed setup. Secret value intentionally not recorded.
- User asked that history-named files always remain in `.gitignore` and directed the assistant to choose the corpus theme autonomously.
- User supplied the GitHub repository URL and authorized pushing the complete project when ready; no push has occurred.

## Blockers / open questions
- None for Step 1.1.

## How to run (kept current)
- Setup: `python -m venv .venv`; `.\\.venv\\Scripts\\Activate.ps1`; `python -m pip install -r requirements.txt`.
- Tests: `.venv\\Scripts\\python.exe -m pytest -m "not gemini"` (22 passed; excludes the separate live API test).
- Gemini check: `.venv\\Scripts\\python.exe scripts/check_gemini.py`.
- Backend: not implemented yet.
- Frontend: not implemented yet.
