# PROGRESS

## NEXT STEP
- Step ID and title: Step 0.2 - Environment check and Ollama setup
- Exactly what to do next: Confirm the machine can run a local LLM and choose the model. Ask the user for OS, RAM, GPU availability, and Ollama installation status. Then provide the external-action steps in PLAN.md Step 0.2 to install Ollama if needed, pull a hardware-appropriate model, and verify it with `ollama list` and `curl http://localhost:11434/api/tags`. After the user replies, set `OLLAMA_MODEL` in `.env`, add `scripts/check_ollama.py`, run an Ollama smoke check, and verify that the configured sentence-transformers embedding model loads.
- Files likely to be touched: `.env`, `scripts/check_ollama.py`, `tests/` (Ollama-marked test), `PROGRESS.md`.
- Pending user input or blockers: OS, RAM, GPU availability, Ollama installation status, chosen/pulled model, and `ollama list` output.

## Current state summary
- Step 0.1 scaffold is implemented; Python 3.11.9 is available.
- Package is `docintel`; configuration uses `pydantic-settings` and supports environment overrides.
- Console and rotating file logging are configured by `configure_logging`.
- Step 0.1 smoke tests: 3 passed, 0 failed with the foundation dependencies installed.
- All requirements in `requirements.txt` are installed in `.venv`; `pip check` reports no broken requirements.
- Step 0.1 regression suite: 3 passed, 0 failed (`.venv\\Scripts\\python.exe -m pytest -m "not ollama"`).
- Major runtime imports (FastAPI, Gradio, ChromaDB, sentence-transformers, PyMuPDF, python-docx, LangChain splitters, Pandas) succeeded.

## Step log
| Step | Title | Status (done/in-progress/blocked) | Date | Tests (unit/integration) | Notes / files created |
|---|---|---|---|---|---|
| 0.1 | Scaffold the repository | done | 2026-10-31 | 3 unit passed / 0 integration | Initial scaffold, config, logging, pytest config, README, and smoke tests created. Git initialized. Requirements installed; `pip check` clean; runtime imports verified. Commit: `step 0.1: Scaffold the repository`. |

## Decisions made
- Project name: `docintel` is the temporary package name until Step 8.1 selects the final brand.
- Ollama model: not chosen; reserved for Step 0.2 with user input.
- Embedding model: `sentence-transformers/all-MiniLM-L6-v2` (locked default from PLAN.md).
- Chunk size/overlap and similarity threshold: provisional PLAN.md defaults (800/100/0.25).

## External actions completed by the user
- None yet.

## Blockers / open questions
- Step 0.2 requires user hardware and Ollama details before selecting or recording an LLM model.

## How to run (kept current)
- Setup: `python -m venv .venv`; `.\\.venv\\Scripts\\Activate.ps1`; `python -m pip install -r requirements.txt`.
- Tests: `.venv\\Scripts\\python.exe -m pytest -m "not ollama"` (3 passed).
- Backend: not implemented yet.
- Frontend: not implemented yet.
