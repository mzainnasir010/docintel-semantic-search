<p align="center">
  <img src="assets/logo.svg" alt="Quillseek" width="360">
</p>

<p align="center">Find answers in your documents, with sources you can check.</p>

## 1. Project Overview

Quillseek is a local-first document ingestion and semantic search application built for the seKer AI internship. It indexes PDF, DOCX, and TXT files on your computer, finds passages by meaning, and can ask Google Gemini to produce a concise answer with source citations.

The document index and uploaded files stay on the machine running Quillseek. For an Ask request, retrieved passages and the question are sent to the configured Gemini API. Do not index confidential documents unless that sharing is acceptable.

## 2. Business Problem

Keyword search misses information when a question and a document use different words for the same idea. For example, a question about “annual leave” may need to find a passage that says “paid vacation days.” Semantic retrieval compares meaning through text embeddings and returns ranked passages with document and page metadata.

## 3. Features

- Ingest PDF, DOCX, and TXT documents with per-file error handling.
- Clean extracted text, preserve page/section metadata, and split it into configurable chunks.
- Embed chunks with `sentence-transformers/all-MiniLM-L6-v2` and store them in a persistent local ChromaDB collection.
- Search by natural-language query, with ranked passages, similarity scores, and document/page details.
- Ask Gemini for a grounded answer with validated source labels; refuse when retrieval has no relevant evidence.
- Use the Gradio interface to upload, index, search, ask, delete documents, and reset the collection.
- Evaluate retrieval from a reviewed 29-question set and inspect per-question outputs in `eval/results/results.csv`.

## 4. Architecture

The Gradio frontend calls the FastAPI backend over HTTP. The backend owns ingestion, embedding, ChromaDB access, retrieval, and Gemini requests.

```mermaid
flowchart LR
  subgraph Indexing["Pipeline A — indexing"]
    Upload["Upload PDF / DOCX / TXT"] --> Load["Route and extract text"]
    Load --> Clean["Clean and preserve page metadata"]
    Clean --> Chunk["Split into chunks"]
    Chunk --> Embed["MiniLM embeddings"]
    Embed --> Store[("ChromaDB — local persistent index")]
  end

  subgraph Query["Pipeline B — search and RAG"]
    Ask["Question"] --> QEmbed["MiniLM query embedding"]
    QEmbed --> Retrieve["Cosine similarity top-K retrieval"]
    Store --> Retrieve
    Retrieve --> SearchOut["Ranked passages and scores"]
    Retrieve --> Prompt["Context-only prompt with source labels"]
    Prompt --> Gemini["Google Gemini Developer API"]
    Gemini --> Answer["Answer, validated citations, or refusal"]
  end

  Browser["Gradio UI"] <-->|"HTTP API"| API["FastAPI + background index jobs"]
  API --> Upload
  SearchOut --> API
  Answer --> API
```

More detail is in [docs/architecture.md](docs/architecture.md) and the API guide is in [docs/api.md](docs/api.md).

## 5. Technology Stack

| Area | Choice | Why this choice / comparison |
|---|---|---|
| API | FastAPI + Uvicorn | Typed request/response models, validation, OpenAPI docs, and background indexing; keeps the service independently testable. |
| Interface | Gradio | Python-native UI suitable for a document-search demo; it calls the backend over HTTP instead of reaching into backend internals. |
| Vector store | ChromaDB, persistent local mode | Stores vectors with document/page metadata and persists between runs. FAISS is a strong vector-search library, but persistence and metadata filtering would need additional application-managed pieces. |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` | A compact 384-dimensional model that can run locally on CPU. Larger embedding models may improve some tasks but use more memory and compute; no alternative model benchmark is claimed here. |
| Answer generation | Gemini Developer API via REST/HTTPX | Hosted generation avoids requiring a local GPU/LLM installation. Ollama or another local model would keep inference on-device but requires installing and running a model and may be slower on modest hardware. |
| Parsing | PyMuPDF and python-docx | Extract PDF pages and DOCX paragraphs/tables while retaining useful source metadata. |
| Chunking | Recursive text splitter plus sentence- and section-aware alternatives | The recorded experiment selected recursive chunks at 1,500 characters with zero overlap; see [docs/CHUNKING_EXPERIMENTS.md](docs/CHUNKING_EXPERIMENTS.md). |
| Configuration and tests | Pydantic Settings, `.env`, pytest | Typed settings with environment overrides, and unit/integration test coverage around the pipeline and API. |

The project was developed on Windows with 16 GB RAM and Intel UHD 620 integrated graphics; the embedding model runs on CPU when a supported GPU is unavailable.

## 6. Installation

Clone the repository and create a Python 3.11+ environment (Python 3.10+ is the code target; the project was verified with Python 3.11):

```powershell
git clone https://github.com/mzainnasir010/docintel-semantic-search.git
cd docintel-semantic-search
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Create or view a Gemini API key in [Google AI Studio](https://aistudio.google.com/apikey), then replace the placeholder for `GEMINI_API_KEY` in the project-root `.env`. The key must stay in `.env` or a private environment variable; never commit it or paste it into source files. Google’s [API key guide](https://ai.google.dev/gemini-api/docs/api-key) explains project/key setup. A configured key can still be subject to project quota limits.

The first embedding run may need internet access to download the configured sentence-transformers model. The model is cached for subsequent runs.

## 7. Configuration

Copy `.env.example` to `.env`. It contains variable names and a safe API-key placeholder; non-secret values are blank. Blank settings use the defaults below. Settings can also be provided through the process environment, which takes precedence over `.env`.

| Variable | Default | Purpose |
|---|---|---|
| `GEMINI_BASE_URL` | `https://generativelanguage.googleapis.com/v1beta` | Gemini REST API base URL. |
| `GEMINI_API_KEY` | unset | Secret used to authenticate Gemini requests. |
| `GEMINI_MODEL` | `gemini-3.8-flash` | Generation model name. |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Same embedding model is used for indexed chunks and queries. Changing it requires rebuilding the index. |
| `EMBEDDING_BATCH_SIZE` | `32` | Number of texts encoded in one embedding batch. |
| `CHROMA_PATH` | `data/chroma` | Local persistent vector database directory. |
| `COLLECTION_NAME` | `documents` | ChromaDB collection name. |
| `UPLOAD_DIR` | `data/uploads` | Local directory for uploaded files. |
| `MAX_UPLOAD_BYTES` | `20971520` (20 MiB) | Maximum accepted upload size per file. |
| `GRADIO_ORIGIN` | `http://127.0.0.1:7860` | Allowed browser origin for the API. |
| `CHUNK_SIZE` | `1500` | Target recursive chunk size in characters. |
| `CHUNK_OVERLAP` | `0` | Character overlap between adjacent chunks. |
| `CHUNK_STRATEGY` | `recursive` | Chunking strategy (`recursive`, `sentence`, or `section`). |
| `TOP_K` | `5` | Default number of search results/sources. |
| `MIN_SIMILARITY` | `0.25` | Similarity threshold below which a result is not considered relevant. |
| `LLM_TEMPERATURE` | `0.1` | Gemini generation temperature. |
| `LLM_MAX_OUTPUT_TOKENS` | `128` | Maximum generated output-token setting. |
| `LLM_THINKING_LEVEL` | `low` | Gemini thinking level used by requests. |
| `RAG_PROMPT_CHAR_BUDGET` | `12000` | Total character limit for the grounded prompt. |
| `API_HOST` | `127.0.0.1` | Host used by backend and frontend launchers. |
| `API_PORT` | `8000` | FastAPI/Uvicorn listening port. |
| `BACKEND_URL` | `http://127.0.0.1:8000` | Base URL the frontend uses for API calls. |
| `UI_PORT` | `7860` | Gradio listening port. |
| `LOG_LEVEL` | `INFO` | Console/file logging level. |

Runtime data directories (`data/chroma/` and `data/uploads/`) and `.env` are ignored by Git.

## 8. Usage

Open two PowerShell terminals in the project directory. Start the backend in terminal 1:

```powershell
.\.venv\Scripts\python.exe scripts/run_backend.py
```

Start the frontend in terminal 2:

```powershell
.\.venv\Scripts\python.exe scripts/run_frontend.py
```

Open `http://127.0.0.1:7860`. In **Documents**, upload supported files and select **Index pending documents**. Search the indexed library in **Search**, or ask a natural-language question in **Ask** and inspect its cited sources. The REST API is at `http://127.0.0.1:8000`; interactive API docs are at [`/docs`](http://127.0.0.1:8000/docs).

To index the bundled corpus from a terminal, run `.\.venv\Scripts\python.exe scripts/index_corpus.py`. To test a search directly, run `.\.venv\Scripts\python.exe scripts/search_cli.py "How do pure paths differ from concrete paths?"`.

Run the non-live suite (uses the cached embedding model):

```powershell
$env:HF_HUB_OFFLINE='1'
Remove-Item Env:GEMINI_API_KEY -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -m pytest -m "not gemini"
```

Live Gemini tests are marked `gemini` and need a working `.env` key, internet access, and available project quota. To run them, clear any stale process override and use `.\.venv\Scripts\python.exe -m pytest -m gemini`. To check a minimal real request, use `.\.venv\Scripts\python.exe scripts/check_gemini.py`.

For retrieval-only metrics without Gemini, run `.\.venv\Scripts\python.exe eval\run_eval.py --skip-rag`. When quota is available, resume answer-level evaluation with `.\.venv\Scripts\python.exe eval\run_eval.py --resume`.

## 9. Example Queries

These examples are measured against the current local index. “Correct” means the top result matches the expected document and page; it does not certify exact answer-bearing chunk relevance. See [docs/SEARCH_EXAMPLES.md](docs/SEARCH_EXAMPLES.md) and [docs/EVALUATION.md](docs/EVALUATION.md) for the measurement limitations.

| Query | Retrieved source | Similarity | Page-level result |
|---|---|---:|---|
| What kind of application code is asyncio described as a good fit for? | `python_asyncio.txt` | 0.619 | Correct |
| Why should an application limit the size of untrusted JSON input? | `python_json.docx` | 0.479 | Correct |
| How do pure paths differ from concrete paths? | `python_pathlib.docx` | 0.472 | Correct |
| What kinds of command-line arguments can `ArgumentParser.add_argument()` describe? | `python_argparse.pdf` | 0.717 | Partial; page 2 is not in top five |
| How do I configure Kubernetes horizontal pod autoscaling for production? | No relevant result | — | Weak match |

## 10. Evaluation

The current retrieval run covers 25 answerable and 4 unanswerable reviewed questions. Relevance is document/page-level, so it can overcount off-topic chunks from single-page text documents.

| K | Hit@K | Precision@K | Recall@K | MRR |
|---:|---:|---:|---:|---:|
| 3 | 0.880 | 0.613 | 0.860 | 0.880 |
| 5 | 0.920 | 0.600 | 0.900 | 0.890 |
| 10 | 0.960 | 0.544 | 0.960 | 0.894 |
| 20 | 1.000 | 0.416 | 1.000 | 0.896 |

K=5 remains the product default: larger candidate sets recovered two lower-ranked gold pages but reduced precision, and generated answer quality has not been measured. Chunking experiments selected recursive 1,500-character chunks with zero overlap: MRR 0.890 and Hit@5 0.920 in that experiment. Full per-question findings and deferred answer-level metrics are in [docs/EVALUATION.md](docs/EVALUATION.md); the chunk sweep is in [docs/CHUNKING_EXPERIMENTS.md](docs/CHUNKING_EXPERIMENTS.md).

**Gemini answer, refusal, citation, token, and API-cost metrics are pending a working key/quota.** The current CSV labels these fields as deferred; they are not presented as passing or zero-cost results.

## 11. Screenshots

Browser automation was unavailable during implementation, so no screenshots are claimed here yet. The exact visual and capture checklist is in [docs/UI_MANUAL_CHECKLIST.md](docs/UI_MANUAL_CHECKLIST.md); requested PNGs belong in `docs/screenshots/`.

## 12. Limitations

- The sample corpus covers Python documentation, not arbitrary enterprise policies or private company material.
- PDF extraction quality depends on machine-readable text; scanned image-only documents need OCR, which is not implemented.
- Page-level evaluation labels are coarse and can count irrelevant chunks from the same document/page as relevant.
- Gemini generation quality, refusal behavior, citation grounding, token usage, and live answer costs remain unverified until a working API key and quota are available.
- The Gemini service requires internet access and is subject to project-specific rate limits. Retrieved passage text is sent to the configured provider for Ask requests.
- The UI was not browser-automated; complete the manual responsive/console checks and capture screenshots before delivery.

## 13. Future Improvements

- Re-run live RAG evaluation and inspect generated citations and refusals when Gemini quota is available.
- Add chunk-level gold evidence spans to reduce page-label scoring ambiguity.
- Explore query-aware retrieval or reranking only after measured before/after tests.
- Add OCR for scanned PDFs and broader, user-approved domain corpora.
- Capture the desktop and narrow-width UI states listed in the manual checklist.
