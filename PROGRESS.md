# PROGRESS

## NEXT STEP
- Step ID and title: Step 4.1 - Embedder
- Exactly what to do next: In `embeddings/`, implement an `Embedder` class wrapping sentence-transformers with lazy singleton loading, configurable batch encoding, L2-normalized outputs, separate `embed_documents(list[str])` and `embed_query(str)` methods using the same model, config-driven model name, and exposed model name/dimension. Detect and use GPU when available, otherwise CPU. Keep embedding model name available for later vector-store metadata and mismatch detection. Add unit tests for output shape/dimension, normalization, deterministic output, batch versus single encoding, empty list, and a semantic sanity comparison between annual leave/vacation phrasing and unrelated text.
- Files likely to be touched: `src/docintel/embeddings/`, `src/docintel/config.py`, `tests/unit/`.
- Pending user input or blockers: None.

## Current state summary
- Step 0.1 scaffold is implemented; Python 3.11.9 is available.
- Package is `docintel`; configuration uses `pydantic-settings` and supports environment overrides.
- Console and rotating file logging are configured by `configure_logging`.
- All requirements in `requirements.txt` are installed in `.venv`; `pip check` reports no broken requirements.
- Gemini `gemini-3.8-flash` is configured and live-verified using the ignored project-root `.env`; the key is not recorded in Git or progress notes.
- Sentence-transformers model loads with embedding dimension 384.
- Corpus: 9 redistributable Python docs (4 TXT, 3 PDF, 2 DOCX), each attributed; `SOURCES.md` and PSF license included.
- Current backend regression suite: 50 passed, 0 failed, 1 live Gemini test deselected (`pytest -m "not gemini"`).
- GitHub destination was supplied by the user; push is deferred until the project is complete.

## Step log
| Step | Title | Status (done/in-progress/blocked) | Date | Tests (unit/integration) | Notes / files created |
|---|---|---|---|---|---|
| 0.1 | Scaffold the repository | done | 2026-10-31 | 3 unit passed / 0 integration | Initial scaffold, config, logging, pytest config, README, and smoke tests created. Git initialized. Requirements installed; `pip check` clean; runtime imports verified. Commit: `step 0.1: Scaffold the repository`. |
| 0.2 | Gemini API setup | done | 2026-10-31 | 7 unit passed / 1 integration passed | Replaced Ollama with Gemini REST API in PLAN.md and GROUND_TRUTH.md; configured `gemini-3.8-flash`; added safe API check script, request-construction tests, and a live test that reads credentials only from local `.env`. Full `pytest`: 8 passed. Embedding model loaded (384 dimensions). Commit: `step 0.2: Gemini API setup`. |
| 0.3 | Corpus assembly | done | 2026-10-31 | 1 unit passed / 3 integration passed | Selected Python technical documentation at the user's direction to choose autonomously. Built 9 documents (4 TXT, 3 PDF, 2 DOCX) from official Python 3.12 docs under PSF License Version 2; retained license/copyright and adaptation note. `SOURCES.md` records each URL/licence. `.gitignore` excludes history-named files/folders. Commit: `step 0.3: Corpus assembly`. |
| 1.1 | Data models and loaders | done | 2026-10-31 | 18 unit passed / 4 integration passed | Added validated shared models, resilient PyMuPDF/DOCX/TXT loaders, PDF date parsing, logical DOCX sections and flattened tables, encoding fallbacks, and generated fixtures. `pytest -m "not gemini"`: 22 passed, 1 deselected. Commit: `step 1.1: Data models and loaders`. |
| 1.2 | Router, multi-document ingestion, error boundaries, stable IDs | done | 2026-10-31 | 21 unit passed / 5 integration passed | Added signature/extension routing, streaming SHA-256 IDs, batch summary and per-file failure records. Mixed-batch integration verifies valid files continue around corrupt and unsupported files. `pytest -m "not gemini"`: 26 passed, 1 deselected. Commit: `step 1.2: Router, multi-document ingestion, error boundaries, stable IDs`. |
| 2.1 | Cleaning functions | done | 2026-10-31 | 27 unit passed / 6 integration passed | Added NFKC normalization, punctuation standardization, control/format cleanup, hyphenation repair, paragraph joining, and whitespace collapse while preserving headings, lists, tables, paragraphs, and case. Added loader-to-cleaner integration coverage. `pytest -m "not gemini"`: 33 passed, 1 deselected. Commit: `step 2.1: Cleaning functions`. |
| 2.2 | Repeated header/footer removal and memory-safe processing | done | 2026-10-31 | 30 unit passed / 8 integration passed | Added page-streaming PDF extraction, two-pass repeated boundary/header/footer detection, normalized printed page numbers, per-page cleanup and metadata retention through batch ingestion, and structured removal reports with logging. Added synthetic and corpus PDF integration coverage plus a before/after example in `docs/`. `pytest -m "not gemini"`: 38 passed, 1 deselected. Commit: `step 2.2: Repeated header/footer removal and memory-safe processing`. |
| 3.1 | Chunkers | done | 2026-10-31 | 39 unit passed / 9 integration passed | Added recursive (LangChain), sentence-based, and section-aware strategies; config-driven factory; stable chunk IDs, source metadata, timestamps, page-local character offsets, overlap, empty filtering, and per-document deduplication. Integration exercises corpus ingestion through preprocessing and chunking. `pytest -m "not gemini"`: 48 passed, 1 deselected. Commit: `step 3.1: Chunkers`. |
| 3.2 | Evaluation question set (external review) | done | 2026-10-31 | 40 unit passed / 10 integration passed | User reviewed/approved six questions and provided corrections for Q-028 and Q-016. Programmatic source audit confirmed Q-010 wording and found `Path.chmod()` / `Path.lchmod()` in pathlib, so invalid unanswerable Q-031 was removed. Final set has 29 questions, 4 unanswerable, and 6 paraphrased. Schema and corpus evidence tests pass; full regression `pytest -m "not gemini"`: 50 passed, 1 deselected. Commit: `step 3.2: Evaluation question set`. |

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
- Tests: `.venv\\Scripts\\python.exe -m pytest -m "not gemini"` (50 passed; excludes the separate live API test).
- Gemini check: `.venv\\Scripts\\python.exe scripts/check_gemini.py`.
- Backend: not implemented yet.
- Frontend: not implemented yet.
