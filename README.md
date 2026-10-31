<p align="center">
  <img src="assets/logo.svg" alt="Quillseek" width="360">
</p>

<p align="center">Find the answer in your documents, with sources you can check.</p>

Quillseek is a local-first document ingestion and semantic search project built during the seKer AI internship. It indexes PDF, DOCX, and TXT files on this machine, retrieves relevant passages, and uses Google Gemini to produce concise, cited answers.

> Your index stays on this machine; retrieved passages are sent to Gemini to answer questions.

## Requirements

- Python 3.11+
- A Gemini Developer API key stored only in the project-root `.env` file

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Add your Gemini key to `.env` as `GEMINI_API_KEY=...`. Keep `.env` private; it is ignored by Git. Other configuration can stay at application defaults. If Windows has an old process-level `GEMINI_API_KEY`, update or clear that environment variable because it takes precedence over `.env`.

## Run the backend

```powershell
.\.venv\Scripts\python.exe scripts/run_backend.py
```

The API defaults to `http://127.0.0.1:8000`. OpenAPI documentation is at [`/docs`](http://127.0.0.1:8000/docs), and endpoint examples are in [docs/api.md](docs/api.md).

## Run the application

Open two PowerShell terminals in the project directory. Start the backend in the first:

```powershell
.\.venv\Scripts\python.exe scripts/run_backend.py
```

Start the frontend in the second:

```powershell
.\.venv\Scripts\python.exe scripts/run_frontend.py
```

Then open `http://127.0.0.1:7860`. The frontend connects to the configured `BACKEND_URL`.

For visual checks, follow [the UI manual checklist](docs/UI_MANUAL_CHECKLIST.md). Browser automation is unavailable in the current environment; capture the requested screenshots during Step 10.2.

## Tests

```powershell
$env:HF_HUB_OFFLINE='1'
Remove-Item Env:GEMINI_API_KEY -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -m pytest -m "not gemini"
```

Live Gemini integration tests are marked `gemini` and require internet access plus an available API quota:

```powershell
Remove-Item Env:GEMINI_API_KEY -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -m pytest -m gemini
```

## Project map

- `src/quillseek/` — application package
- `data/sample_docs/` — attributed Python documentation corpus
- `eval/` — reviewed questions and retrieval evaluation
- `docs/` — API guide and experiment reports
- `tests/` — unit and integration tests
- `PLAN.md` and `PROGRESS.md` — project plan and step-by-step build record
