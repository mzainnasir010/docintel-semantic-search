# PLAN.md — AI-Powered Document Intelligence & Semantic Search System

> seKer AI · AI & ML Internship · Project 05
> This file is the single source of truth for HOW to build the project, step by step.
> Companion files: `GROUND_TRUTH.md` (what "finished" means) and `PROGRESS.md` (live status, created and maintained by you).

---

## 1. What this project is

### 1.1 The problem
Organisations hold huge piles of documents (policies, manuals, reports, papers) that nobody can search effectively. Keyword search only matches the exact words typed, but people search by intent while documents are written in formal language.

Example: the user asks *"How many days of annual leave can an employee take?"* and the document says *"Employees are entitled to twenty paid vacation days per calendar year."* Almost no words overlap, so keyword search fails. This project works on **meaning** instead of spelling.

### 1.2 The solution
Build an end-to-end application that:
1. Ingests documents (PDF, DOCX, TXT), cleans the text and splits it into chunks.
2. Converts each chunk into an embedding (a vector representing its meaning) and stores it in a vector database together with metadata (document name, page, etc.).
3. Takes a natural-language question, embeds it with the SAME model, and retrieves the Top-K most similar chunks with similarity scores (semantic search).
4. Passes those chunks to Google Gemini through the Gemini Developer API in a RAG prompt so it writes an answer **grounded only in the retrieved context**, with source citations (document + page).
5. If the documents do not contain the answer, the system says so plainly instead of making something up. Graders explicitly test for this.

### 1.3 The two pipelines

```
PIPELINE A: INDEXING (runs when documents are added)
Upload -> Loader/Router -> Text Extraction -> Cleaning -> Chunking -> Embedding -> Vector DB (+ metadata)

PIPELINE B: QUERY + RAG (runs on every question)
Question -> Query Embedding (same model) -> Top-K Similarity Search -> Ranked Chunks
         -> RAG Prompt (instructions + context + question) -> LLM -> Grounded Answer + Sources
```

### 1.4 What gets assessed
Not just "does it run". Assessors look at: modular clean code, per-file error handling, measured retrieval quality (Precision@K, Recall@K, MRR), honest error analysis, grounded answers with citations, professional UI, secure key handling, reproducibility, and documentation. Full list in `GROUND_TRUTH.md`.

---

## 2. Locked decisions (do not change without asking the user)

| Layer | Choice |
|---|---|
| Language | Python 3.10+ |
| Backend | FastAPI (+ Uvicorn) |
| Frontend | Gradio, calling the FastAPI backend over HTTP |
| Vector DB | ChromaDB (persistent, local, cosine similarity) |
| Embeddings | `sentence-transformers`, default `all-MiniLM-L6-v2` (configurable) |
| LLM | Google Gemini Developer API, called through REST with `httpx`; model chosen in Step 0.2 |
| PDF / DOCX parsing | PyMuPDF (`pymupdf`), `python-docx` |
| Chunking | `langchain-text-splitters` (recursive) plus custom sentence-based and section-aware splitters |
| Config | `pydantic-settings` + `.env` |
| Tests | `pytest` |
| Evaluation | NumPy / Pandas |

No model training or fine-tuning is needed anywhere. All models are pre-trained and used as-is.

---

## 3. Target repository structure

Create exactly this layout (add files as needed, keep it modular):

```
<project-root>/
├── PLAN.md
├── GROUND_TRUTH.md
├── PROGRESS.md                 # you create and maintain
├── README.md
├── requirements.txt
├── .env.example                # variable names only; Gemini API key uses a safe placeholder
├── .gitignore                  # root settings and shared ignore rules
├── backend/
│   ├── src/quillseek/          # config, models, ingestion, preprocessing, chunking,
│   │                           # embeddings, vectorstore, indexing, search, rag, API
│   └── scripts/                # backend launcher, indexing/search CLI, Gemini check
├── frontend/
│   ├── src/quillseek_frontend/ # Gradio app, API client, theme, formatting, CSS
│   ├── frontend/scripts/run_frontend.py
│   └── assets/                 # logo and favicon
├── data/
│   ├── sample_docs/            # public corpus (committed)
│   ├── uploads/                # runtime uploads (gitignored)
│   └── chroma/                 # vector DB persistence (gitignored)
├── docs/                       # architecture, evaluation, screenshots, guides
├── eval/                       # questions, runners and results
├── scripts/                    # shared corpus/security/documentation utilities
└── tests/                       # unit and integration coverage for both apps
    ├── conftest.py
    ├── unit/
    └── integration/
```

---

## 4. Working rules (follow strictly)

### 4.1 The loop (repeat for every step)
1. Read `PLAN.md`, `GROUND_TRUTH.md`, and `PROGRESS.md` (if it exists). Resume from the "NEXT STEP" recorded in `PROGRESS.md`.
2. Implement **only the current step**. Do not jump ahead.
3. Write tests for everything the step adds (see section 6).
4. Run the new tests AND the full existing regression suite. Fix until everything passes.
5. Only when everything passes: update `PROGRESS.md` (see section 5), commit locally (`git commit -m "step X.Y: <title>"`), then move to the next step.
6. If a step needs something from the user (section 7), STOP and ask. Do not guess or fabricate values.

### 4.2 Hard rules
- **Backend first, frontend after.** Phases 0-7 are backend, Phase 8 is frontend.
- Never hardcode secrets, URLs or paths. Read from config/env. Never commit `.env`.
- One embedding model for corpus and queries. If it changes, re-index everything.
- Never delete, skip or weaken a failing test just to get green. Fix the code.
- If the same failure persists after 3 genuine fix attempts, record it under "Blockers" in `PROGRESS.md` and ask the user.
- Keep functions small, typed, documented, and logged. Use meaningful names and proper error handling.
- Do not tick items in `GROUND_TRUTH.md` until the final audit (Step 11.1).
- Do not add optional/advanced features unless the user asks after Phase 11.

---

## 5. PROGRESS.md specification

Create `PROGRESS.md` at Step 0.1 and update it **immediately after each completed step** (not at the end). It must be good enough that a different AI model, with zero memory of this session, can continue the work after credits run out.

Required structure:

```markdown
# PROGRESS

## NEXT STEP  (always keep this section at the top and current)
- Step ID and title: e.g. "Step 2.1 - Cleaning functions"
- Exactly what to do next (copy the step's goal from PLAN.md)
- Files likely to be touched
- Any pending user input or blockers that affect it

## Current state summary
- 3-6 lines: what works now, how to run it, current test status (counts of passed/failed)

## Step log
| Step | Title | Status (done/in-progress/blocked) | Date | Tests (unit/integration) | Notes / files created |

## Decisions made
- Chosen project name, Gemini model, embedding model, chunk size/overlap, thresholds, and why

## External actions completed by the user
- What the user did (e.g. configured Gemini API access, approved corpus) and non-secret values they returned

## Blockers / open questions

## How to run (kept current)
- Setup, run backend, run frontend, run tests (exact commands)
```

---

## 6. Testing rules

- Create tests for **every feature** you build. Location: `tests/unit/` (single function/class, no network, no real LLM) and `tests/integration/` (several components working together).
- Use `pytest`. Register markers in `pytest.ini` / `pyproject.toml`: `integration`, `gemini` (needs a configured Gemini API key and network access). Live Gemini tests must skip gracefully when credentials or the API are unavailable.
- Generate tiny test fixtures programmatically (small PDF/DOCX/TXT files, including an empty file, an image-only page, a corrupt file, odd encodings). Do not depend on large files.
- Unit tests mock the LLM and (where slow) the embedding model. Integration tests use the real embedding model and a temporary Chroma directory.
- Each step must add an integration test when it connects components (e.g. ingest -> preprocess -> chunk; index -> search; API endpoints via FastAPI `TestClient`).
- **Gate:** run `pytest -m "not gemini"` (full regression) after every step, and `pytest -m gemini` on steps that touch the LLM when a key is configured. Move on only when everything passes. Record counts in `PROGRESS.md`.
- Expose a single command to run everything (e.g. `pytest`).

---

## 7. External-work protocol

Some things only the user can do (installing software, creating accounts, supplying links, approving data, recording a video). When a step needs one:
1. **Stop coding** for that item and write a clearly marked block in the chat:
   `EXTERNAL ACTION REQUIRED`
2. Give **detailed numbered steps** (exact commands/links/clicks), the **expected result** so they can verify it, and **exactly what to send back** (e.g. output of a command, a path). Never ask for secrets to be pasted into chat or committed.
3. Record it in `PROGRESS.md` under blockers/external actions, then continue only after the user replies.

Known external items: Gemini API key creation and configuration (Step 0.2), corpus domain approval (Step 0.3), review of the evaluation questions (Step 3.2), screenshots if automation fails (Step 10.2), GitHub remote + push (Step 10.2), LinkedIn video and post + seKer AI submission (user-only, after Step 11.1).

---

## 8. Configuration (env variables)

Provide `.env.example` with the variable names below. Keep all non-secret values blank; the Gemini API key uses the literal placeholder `your-api-key-here`, never a real key. Load runtime values via `pydantic-settings` in `config.py`:

```
GEMINI_BASE_URL=
GEMINI_API_KEY=your-api-key-here
GEMINI_MODEL=
EMBEDDING_MODEL=
CHROMA_PATH=
COLLECTION_NAME=
UPLOAD_DIR=
CHUNK_SIZE=
CHUNK_OVERLAP=
CHUNK_STRATEGY=
TOP_K=
MIN_SIMILARITY=
LLM_TEMPERATURE=
API_HOST=
API_PORT=
BACKEND_URL=
UI_PORT=
LOG_LEVEL=
```

`CHUNK_*`, `TOP_K` and `MIN_SIMILARITY` are provisional until Step 5.3 decides them with evidence.

---

## 9. Frontend branding and design brief (applies in Phase 8)

- **Colour theme (use exactly these):**
  - Deep Blue `#09318D` (primary: header, headings, primary buttons)
  - Pure White `#FFFFFF` (backgrounds, cards)
  - Bubblegum Pink `#FD91CC` (accents: highlights, hover states, badges, score pills, focus rings)
  - Neutral tints derived from these are allowed (e.g. very light blue/grey for borders and subtle surfaces). Keep text contrast accessible: use deep blue or near-black text, never pink text on white for body copy.
- **Project name:** choose ONE simple, unique, memorable one-word name (not an existing well-known product; short; easy to spell; suggestive of documents, meaning or search). Record it in `PROGRESS.md` and use it consistently in the UI, README, package name, and docs.
- **Logo:** design an original SVG logo (`frontend/assets/logo.svg`, plus `frontend/assets/favicon.svg`) using only the theme colours: a simple modern mark (e.g. a document/page combined with a spark, magnifier or speech bubble) plus the wordmark. Use it in the **header and footer** of the UI, and in the README.
- **Style:** modern, clean, generous whitespace, rounded corners, soft shadows, card-based layout, subtle hover/transition effects, responsive. Header: deep blue bar with logo, name and a short tagline. Footer: logo, name, "Built during the seKer AI internship", and a truthful privacy note: "Your index stays on this machine; retrieved passages are sent to Gemini to answer questions."
- Implement with a custom Gradio theme (`gr.themes.Base` customised) plus a small CSS file. Frontend talks only to the backend API (no business logic in the UI).

---

## 10. The steps

Each step has: **Goal**, **Codex prompt** (what to build), **Tests**, **Done when**.
Phases: 0 Foundation · 1 Ingestion · 2 Preprocessing · 3 Chunking · 4 Embeddings and Vector Store · 5 Semantic Search · 6 RAG · 7 Backend API · 8 Frontend · 9 Evaluation · 10 Documentation · 11 Final Audit.

---

### PHASE 0 — Foundation

#### Step 0.1 — Scaffold the repository
**Goal:** project skeleton, tooling, config, logging, progress tracking.
**Codex prompt:**
```text
Create the repository structure from PLAN.md section 3 in the current directory (empty package folders with __init__.py are fine). Create requirements.txt (fastapi, uvicorn[standard], python-multipart, gradio, chromadb, sentence-transformers, pymupdf, python-docx, langchain-text-splitters, httpx, pydantic, pydantic-settings, python-dotenv, numpy, pandas, pytest, pytest-cov), .gitignore (include .env, data/chroma, data/uploads, .venv, __pycache__), .env.example (from PLAN.md section 8, placeholder only for `GEMINI_API_KEY` and blank other values), config.py using pydantic-settings, logging_config.py (console + rotating file logs), pytest config with markers `integration` and `gemini`, and a README.md stub. Initialise git. Create PROGRESS.md using the structure in PLAN.md section 5 with NEXT STEP = Step 0.2. Create a virtual environment and install requirements. Write a smoke test that imports the package and loads config.
```
**Tests:** config loads defaults; env override works; logging initialises.
**Done when:** `pytest` passes, git repo initialised, `PROGRESS.md` exists.

#### Step 0.2 — Gemini API setup  *(EXTERNAL)*
**Goal:** configure access to a hosted Gemini LLM and choose the model.
**Codex prompt:**
```text
Use Google Gemini Developer API via REST and `httpx`; do not use a local Ollama server. The user has a Windows machine with 16 GB RAM and Intel UHD 620 integrated graphics, which is not a constraint for a hosted model. Use `gemini-3.8-flash` as the initial model choice (official model documentation currently lists it as a stable Flash model suited to new projects). Tell the user to create an API key in Google AI Studio and store it only in the project-root `.env` as `GEMINI_API_KEY=...`; never ask them to paste the key in chat. In `.env.example`, use `GEMINI_API_KEY=your-api-key-here` and leave other values blank. Set `GEMINI_MODEL=gemini-3.8-flash` and `GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta`. Write `backend/scripts/check_gemini.py` that sends one short test prompt using the official `generateContent` REST endpoint with the key in the `x-goog-api-key` header (never in the URL), then prints the reply and latency without printing the key. Add a `gemini`-marked live test that skips gracefully when credentials/network are unavailable. Also verify the sentence-transformers embedding model downloads and loads (first run needs internet).
```
**Tests:** `gemini`-marked test that calls the configured API and gets a non-empty reply (skips gracefully if key/network is unavailable); unit tests for request construction that do not need a real key.
**Done when:** user configured Gemini API access locally; selected model check succeeds; embedding model loads; decision recorded in `PROGRESS.md`.

#### Step 0.3 — Corpus assembly  *(EXTERNAL approval)*
**Goal:** a legal, public corpus of 5-15 related-but-distinct documents (PDF, DOCX, TXT mix).
**Codex prompt:**
```text
Propose 2-3 corpus themes to the user (e.g. open-access AI/ML research papers from arXiv, public government/NGO policy reports, public product or technical documentation, public-domain educational material) and ask them to pick one. Then assemble 5-15 documents on that theme that are public, legally redistributable and contain no personal or confidential data, covering related but DISTINCT subjects so retrieval must discriminate. Include at least one DOCX and one TXT (convert or create from public material if needed) alongside PDFs. Download what you can with backend/scripts/build_corpus.py into data/sample_docs/ and write data/sample_docs/SOURCES.md listing each file, source URL and licence. If downloads are blocked, give the user a list of links and instructions to download them manually into data/sample_docs/, and wait.
```
**Tests:** a test asserting the corpus folder has 5-15 files of the allowed types and SOURCES.md covers each file.
**Done when:** corpus present, documented, approved by the user.

---

### PHASE 1 — Document Ingestion (Module M1, DEV)

#### Step 1.1 — Data models and loaders
**Goal:** extract text plus metadata from PDF, DOCX, TXT.
**Codex prompt:**
```text
In models.py define typed models: DocumentRecord (doc_id, doc_name, source_path, file_type, num_pages, created_at/ingested_at, status), PageContent (doc_id, doc_name, page_number, section (optional), text), and later-used Chunk and SearchResult placeholders. In ingestion/ implement three loaders: PDF (PyMuPDF; per-page text, page numbers, creation date from metadata; image-only/empty pages return empty text with a warning, never crash), DOCX (python-docx; paragraphs, headings captured as section, tables flattened to readable text; DOCX has no real pages so use logical page 1 or section-based units and document this), TXT (try utf-8, then utf-8-sig, then latin-1/cp1252 fallback; replace undecodable characters; treat as a single unit or paragraph blocks). Each loader returns a list of PageContent and never raises on content problems.
```
**Tests:** unit tests per loader using generated fixtures (multi-page PDF, empty PDF page, image-only PDF page, DOCX with headings and a table, TXT in utf-8 and latin-1, empty file).
**Done when:** all loader tests pass.

#### Step 1.2 — Router, multi-document ingestion, error boundaries, stable IDs
**Goal:** ingest many files robustly in one run.
**Codex prompt:**
```text
Implement an ingestion service: detect file type by extension and content signature and route to the right loader; reject unsupported types with a clear error result (not an exception that kills the run). Generate a stable doc_id (short SHA-256 of file content) so re-ingesting the same file is idempotent and a stable doc_name (file name). Process a list of files in one run, wrapping EACH file in its own try/except: on failure, log what failed and why, record status=failed with the error message, and continue with the next file. Return a summary object (succeeded, failed with reasons, page counts). Handle large files without loading everything unnecessarily (iterate pages).
```
**Tests:** unit (routing, ID stability, unsupported type); integration: a batch containing good files plus a corrupt PDF plus an unsupported file completes, the good ones succeed and the failures are reported.
**Done when:** batch ingestion survives bad files and tests pass.

---

### PHASE 2 — Text Preprocessing (Module M2, AI/NLP)

#### Step 2.1 — Cleaning functions
**Goal:** documented, repeatable cleaning.
**Codex prompt:**
```text
In preprocessing/ implement small pure functions and a `clean_text(text)` pipeline: unicode normalisation (NFKC), standardise quotes/dashes/ellipses, remove control characters and zero-width characters, fix hyphenation across line breaks ("exam-\nple" -> "example"), join broken lines inside paragraphs while preserving paragraph boundaries, collapse repeated spaces and excessive blank lines. Preserve meaningful structure: headings, bullet/numbered lists, and table-like content must not be flattened into one blob. Do not lowercase everything (casing carries meaning for embeddings); document that decision in the module docstring.
```
**Tests:** unit tests for each function with before/after examples, including lists, headings, hyphenation, weird unicode, empty input.
**Done when:** tests pass; docstrings explain what and why.

#### Step 2.2 — Repeated header/footer removal and memory-safe processing
**Goal:** remove boilerplate that pollutes embeddings.
**Codex prompt:**
```text
Implement detection and removal of repeated headers, footers and standalone page numbers across the pages of a document (e.g. lines appearing at the top/bottom of a large fraction of pages, normalised for varying page numbers like "Page 3 of 17"). Wire it so a full document goes loader -> per-page cleaning -> cross-page boilerplate removal, processing page by page/generator style to keep memory low on long documents. Keep page numbers in metadata even when page-number text is stripped. Add a short report of what was removed (for logs and for the README).
```
**Tests:** unit (header/footer detection on synthetic pages, page-number variants, no false removal of real content); integration: ingest sample PDF(s) from the corpus then preprocess and assert boilerplate gone, content kept, page metadata intact.
**Done when:** tests pass and a before/after example is saved to `docs/` for the README.

---

### PHASE 3 — Chunking (Module M3, AI)

#### Step 3.1 — Chunkers
**Goal:** multiple strategies behind one interface, each chunk carrying metadata.
**Codex prompt:**
```text
In chunking/ implement a common interface and three strategies: (1) recursive character splitting (langchain-text-splitters; paragraph -> sentence -> word -> char), (2) sentence-based splitting (group whole sentences up to a size limit), (3) section-aware splitting (split on headings/structure when available, then fall back to recursive inside long sections). All take chunk_size and chunk_overlap and a factory selects the strategy from config. Every chunk must carry: chunk_id (stable, e.g. doc_id + page + index), doc_id, doc_name, page_number (or page range), section/heading if known, source_path, ingestion timestamp, and char offsets. Chunks must never span documents. Skip empty/whitespace-only chunks and de-duplicate identical chunks within a document. Default provisional config: recursive, 800 characters, 100 overlap.
```
**Tests:** unit (size limits respected, overlap present, no empty chunks, metadata complete, stable IDs across runs, boundary behaviour on a sentence/table); integration: ingest -> preprocess -> chunk a corpus document.
**Done when:** tests pass.

#### Step 3.2 — Evaluation question set  *(EXTERNAL review)*
**Goal:** 20-30 questions with known answers, used for chunking experiments and final evaluation.
**Codex prompt:**
```text
Read the corpus and write eval/questions.json with 25-30 questions. Each item: id, question, expected_doc_name, expected_page(s), a short expected_answer, and type: one of "direct", "paraphrased" (vocabulary differs from the document, to prove semantic search), "multi_chunk" (answer spans several chunks), "unanswerable" (topic related to the corpus but NOT answered by it, to test refusal; 4-5 of these). Questions must be natural, like real users would ask, and every answerable one must be verifiable against the actual page. Then give the user an EXTERNAL ACTION REQUIRED block: ask them to spot-check at least 8 questions against the source pages and report any wrong ones, then fix them.
```
**Tests:** schema validation test (all fields present, referenced docs exist in corpus, pages within range, at least 4 unanswerable and 5 paraphrased).
**Done when:** the user confirmed; schema test passes.

---

### PHASE 4 — Embeddings and Vector Store (Modules M4 and M5, AI + DEV)

#### Step 4.1 — Embedder
**Goal:** one consistent embedding component.
**Codex prompt:**
```text
In embeddings/ implement an Embedder class wrapping sentence-transformers with: lazy singleton loading, batch encoding with configurable batch size, L2-normalised outputs, separate embed_documents(list[str]) and embed_query(str) methods (both use the SAME model), model name read from config, and a property exposing model name and dimension. Detect and use GPU if available, else CPU. Store the embedding model name in the collection metadata later so a mismatch between index and query model is detected and raises a clear error.
```
**Tests:** unit (shape/dimension, normalisation, deterministic output, batch equals single, empty list); a semantic sanity test that "annual leave days" is closer to "twenty paid vacation days per year" than to an unrelated sentence.
**Done when:** tests pass.

#### Step 4.2 — Vector store (ChromaDB)
**Goal:** persistent index with metadata.
**Codex prompt:**
```text
In vectorstore/ implement a ChromaDB wrapper using a persistent client at CHROMA_PATH, collection COLLECTION_NAME with cosine distance (hnsw:space=cosine). Methods: add_chunks(chunks, embeddings) (upsert by chunk_id so re-indexing is idempotent), query(embedding, k, optional metadata filter such as doc_id) returning chunks with similarity = 1 - cosine_distance, delete_document(doc_id), list_documents() (doc_id, doc_name, chunk count, pages), count(), reset() (delete and recreate the collection). Store in metadata per vector: doc_id, doc_name, chunk_id, page_number, section, source_path, ingested_at. Save the embedding model name in collection metadata and verify it on open. Persistence must survive process restarts.
```
**Tests:** unit/integration with a temp directory: add/query/delete/reset, upsert idempotency, similarity ordering, persistence across re-instantiation, metadata round-trip, model-mismatch error.
**Done when:** tests pass.

#### Step 4.3 — Indexing pipeline orchestrator
**Goal:** documents in, searchable index out with no manual steps.
**Codex prompt:**
```text
In backend/src/quillseek/indexing/ implement `index_files(paths, progress_callback)` that runs the full Pipeline A: ingest (with per-file error boundaries) -> preprocess -> chunk -> embed in batches -> store. It must report progress via the callback (current file, stage, percent, counts), skip documents already indexed with identical content (by doc_id), continue past failed files, and return a summary (indexed, skipped, failed with reasons, chunk counts, elapsed time). Also implement index_directory(path). Record indexing time per run for later evaluation. Add backend/scripts/index_corpus.py to index data/sample_docs.
```
**Tests:** integration: index a temp mix of good/bad files, verify counts, idempotent second run (all skipped), progress callback called monotonically, failures reported not raised; run the script on the real corpus once and record the time.
**Done when:** corpus indexes end to end; tests pass.

---

### PHASE 5 — Semantic Search (Module M5, AI)

#### Step 5.1 — Search service
**Goal:** Top-K retrieval with scores.
**Codex prompt:**
```text
In backend/src/quillseek/search/ implement SearchService.search(query, k, min_similarity, doc_filter) that embeds the query, queries the vector store, returns results sorted by similarity descending with fields: chunk text, doc_name, doc_id, page_number, section, chunk_id, similarity score, and rank. Apply the MIN_SIMILARITY threshold (return an empty list plus a flag when nothing is relevant). Validate inputs (empty query, k bounds). Add backend/scripts/search_cli.py for manual testing.
```
**Tests:** unit (ordering, threshold, empty index, empty query); integration on the corpus: a paraphrased query retrieves the right document in the top results.
**Done when:** tests pass.

#### Step 5.2 — Worked examples table
**Goal:** the README table of real queries and real results.
**Codex prompt:**
```text
Write backend/scripts/make_search_examples.py that runs 8-10 diverse queries (including paraphrased ones and one weak/off-topic one) against the real index and writes docs/SEARCH_EXAMPLES.md with a table: Example query | Retrieved document and page | Similarity | Result (Correct / Partial / Weak match). Judge correctness against the eval questions' expected sources, not by guesswork. Use real measured values only.
```
**Tests:** a test that the script runs and the generated table has the right columns and rows.
**Done when:** `docs/SEARCH_EXAMPLES.md` generated.

#### Step 5.3 — Chunking experiments and final decision
**Goal:** evidence-based chunk size/overlap/strategy.
**Codex prompt:**
```text
Write eval/chunking_experiments.py that re-indexes the corpus into a temporary collection for each configuration and measures retrieval on eval/questions.json (answerable questions only): Hit@K / Precision@K / Recall@K / MRR plus average chunk length and chunk count. Compare: chunk sizes small (~300), medium (~800), large (~1500) characters; overlap 0 vs ~100-150; strategies recursive vs sentence-based vs section-aware (section-aware only where the corpus has headings). Save raw results to eval/results/chunking.csv and write docs/CHUNKING_EXPERIMENTS.md: the table, the chosen strategy/size/overlap, and a concrete description of what went wrong with rejected settings (e.g. chunks too small to carry an answer, too large to rank precisely, boundary-cut answers). Update .env.example defaults and the chosen config in PROGRESS.md.
```
**Tests:** a fast test of the experiment harness on a tiny corpus; metrics functions unit-tested with hand-computed expected values (put the metrics in `eval/metrics.py` so Step 9.1 reuses them).
**Done when:** decision documented with evidence; defaults updated; full index rebuilt with the chosen config.

---

### PHASE 6 — RAG (Module M6, AI)

#### Step 6.1 — Gemini API client
**Goal:** a thin, mockable hosted LLM layer.
**Codex prompt:**
```text
In rag/ implement an LLMClient interface with a GeminiClient using `httpx` against `{GEMINI_BASE_URL}/models/{GEMINI_MODEL}:generateContent` and `:streamGenerateContent` for streaming; send the API key in the `x-goog-api-key` header, model and temperature from config, with timeout handling. Implement non-streaming `generate()` plus a streaming generator `stream()`. Handle invalid API key, unavailable model, quota/rate limits, API errors, network failures and timeouts with clear typed exceptions. Keep the client swappable (the RAG service depends on the interface, not directly on Gemini).
```
**Tests:** unit with httpx mocked (success, streaming, unavailable, invalid key, model missing, rate limit, timeout); `gemini`-marked live test.
**Done when:** tests pass.

#### Step 6.2 — Prompt builder and RAG service
**Goal:** grounded, cited answers and honest refusals.
**Codex prompt:**
```text
Implement the prompt builder: a system instruction + a clearly delimited CONTEXT block where every chunk is labelled [S1], [S2]... with its document name and page + the user QUESTION. The instruction must say: answer using ONLY the provided context; cite sources inline like [S1] for each claim; if the context does not contain enough information reply exactly that "the answer is not present in the supplied documents" and do not use outside knowledge; be concise. Implement RAGService.ask(question, k): retrieve with SearchService; if nothing passes MIN_SIMILARITY, return the refusal WITHOUT calling the LLM; otherwise build the prompt, call the LLM, parse/validate citations, and return {answer, sources (doc name, page, section, similarity, snippet, label), retrieved_chunks, latency breakdown (retrieval ms, generation ms), refused flag}. Guard the context length (reduce K or truncate chunks if the prompt would exceed a configured budget). Also add a retrieval-only mode for the Search tab.
```
**Tests:** unit with a mocked LLM (prompt contains instruction, labelled context, question; refusal path skips the LLM; source mapping correct; context budget respected); integration with a stub LLM against the real index.
**Done when:** tests pass.

#### Step 6.3 — Grounding and refusal validation (live)
**Goal:** prove the LLM stays grounded.
**Codex prompt:**
```text
Using the configured real Gemini model, run the answerable eval questions and the unanswerable ones through RAGService. Write `gemini`-marked tests asserting: unanswerable questions produce a refusal or "not present" answer (no invented facts), and several answerable questions return an answer containing the expected key fact with a citation to the expected document. If the model hallucinates, tighten the prompt (format, few-shot refusal example, lower temperature) and re-test. Record prompt iterations and findings in PROGRESS.md (they feed the error analysis).
```
**Tests:** the live tests above.
**Done when:** refusals work on all unanswerable questions, or remaining failures are documented honestly with a mitigation.

---

### PHASE 7 — Backend API (Module M7, DEV)

#### Step 7.1 — FastAPI application and routes
**Goal:** clean REST API over the services.
**Codex prompt:**
```text
In backend/src/quillseek/api/ build the FastAPI app with Pydantic request/response schemas and these routes: GET /health (API status, Gemini API configured/reachable status, model name, embedding model, chunk count); POST /documents/upload (multipart, multiple files; validate type and size; save to UPLOAD_DIR; sanitise file names); GET /documents (indexed documents with chunk counts and pages, plus uploaded-but-not-indexed files); DELETE /documents/{doc_id}; POST /index (index all pending uploads, returns a job id); GET /index/status/{job_id} (stage, current file, percent, counts, errors, finished flag); POST /search {query, k} -> ranked chunks with scores; POST /ask {query, k} -> answer + sources + latency; DELETE /collection (reset index and uploads). Use dependency injection for services, consistent error responses (no stack traces), CORS enabled for the Gradio origin, request logging, and auto-generated OpenAPI docs. Add backend/scripts/run_backend.py.
```
**Tests:** unit for schemas/validation; integration with FastAPI TestClient and a temp Chroma dir and stub LLM for every route (happy path, empty index, bad file type, oversize file, unknown job id, reset).
**Done when:** all routes tested.

#### Step 7.2 — Background indexing jobs and end-to-end API test
**Goal:** indexing never freezes the client.
**Codex prompt:**
```text
Implement a job manager so POST /index runs the indexing pipeline in a background thread/task, updating an in-memory job record through the progress callback; GET /index/status/{job_id} returns live progress; prevent two concurrent index jobs on the same collection; ensure search/ask still work while indexing runs. Add an end-to-end integration test that uploads the corpus through the API, starts indexing, polls status until finished, searches, and asks (stub LLM; plus a `gemini` live variant). Document all endpoints with examples in docs/api.md.
```
**Tests:** as described, plus concurrency guard test.
**Done when:** the full backend flow works through HTTP only; full test suite green. **Backend is now complete; record that in `PROGRESS.md`.**

---

### PHASE 8 — Frontend (Module M8, DEV) — start only after Phase 7 is green

#### Step 8.1 — Brand identity: name, logo, theme
**Goal:** project identity and design system.
**Codex prompt:**
```text
Follow PLAN.md section 9. Choose the one-word project name (tell the user which name you chose and why, but do not wait for approval unless they object), rename the package/README titles accordingly, create frontend/assets/logo.svg and frontend/assets/favicon.svg using only #09318D, #FFFFFF and #FD91CC (modern, simple, works at small sizes and on both white and deep blue backgrounds, so provide a light and dark variant if needed), create frontend/src/quillseek_frontend/theme.py (a custom gr.themes.Base theme with the three brand colours) and frontend/src/quillseek_frontend/styles.css (header, footer, cards, buttons, score pills, source cards, answer card, empty states, responsive rules, subtle transitions). Record the name and design tokens in PROGRESS.md.
```
**Tests:** assets exist and are valid XML/SVG; theme module imports; CSS file loads; a test that the brand colour constants equal the three required hex values.
**Done when:** identity assets and theme exist.

#### Step 8.2 — App shell and Documents tab
**Goal:** header/footer layout and document management.
**Codex prompt:**
```text
Build frontend/src/quillseek_frontend/app.py (Gradio Blocks, brand theme, CSS) that talks ONLY to the backend via an API client module (frontend/src/quillseek_frontend/api_client.py using httpx and BACKEND_URL; handle backend-down errors with friendly messages). Layout: header (logo, name, tagline, backend/Gemini status indicator from /health) and footer (logo, name, internship credit, privacy note) on every view, with tabs: Documents, Search, Ask. Documents tab: multi-file upload (PDF/DOCX/TXT), a table of uploaded/indexed documents (name, type, pages, chunks, status), an "Index documents" button with a visible progress bar and live status text driven by polling /index/status (the screen must never look frozen), per-file failure messages, a "Delete document" action, and a "Clear collection" button with a confirmation step. Include a friendly empty state when nothing is uploaded. Add frontend/scripts/run_frontend.py.
```
**Tests:** unit tests for api_client (mocked httpx: success, backend down, error payloads); a smoke test that the Gradio app object builds without error; integration test of the client against the TestClient/live backend where practical.
**Done when:** a document can be uploaded, indexed with progress, listed, deleted and cleared from the UI.

#### Step 8.3 — Search and Ask tabs
**Goal:** inspectable retrieval and grounded answers.
**Codex prompt:**
```text
Search tab: query box, K slider, results as cards showing rank, document name, page/section, the chunk text (with the matching passage readable), and a similarity score pill (pink accent, deep blue text), sorted by score. Ask tab: chat-style or single Q&A layout with a clear answer card that is VISUALLY DISTINCT from the sources panel below/beside it; sources listed as cards (label [S1], document, page, similarity, expandable snippet); show a clear "not found in the documents" state style when the answer is a refusal; show latency; show a spinner/streaming state while generating; disable buttons during requests; handle backend/Gemini API errors gracefully; empty state before any document is indexed pointing the user to the Documents tab. Provide 3-4 example question buttons derived from the corpus.
```
**Tests:** unit tests for the formatting helpers that render result/source cards (HTML strings include score, doc name, page; refusal styling); smoke test of the full UI build.
**Done when:** search and ask work from the UI end to end.

#### Step 8.4 — Polish and UI end-to-end verification
**Goal:** portfolio-grade finish.
**Codex prompt:**
```text
Review the UI against PLAN.md section 9 and the UI items in GROUND_TRUTH.md: consistent spacing, hover and focus states, responsive layout (check narrow widths), contrast of text on all three brand colours, logo visible in header and footer, favicon set, page title set, no console errors. Add a one-command launcher (scripts/run_all.py or a documented two-command flow) that starts backend then frontend. If Playwright is available, add an end-to-end browser test (upload -> index -> search -> ask) and capture screenshots into docs/screenshots/; if not, mark screenshots as a user task for Step 10.2.
```
**Tests:** the e2e test (marked `integration`) or documented manual checklist if Playwright is unavailable.
**Done when:** the UI is complete and verified against the checklist.

---

### PHASE 9 — Evaluation and Error Analysis (Module M9, AI)

#### Step 9.1 — Evaluation runner
**Goal:** measured results.
**Codex prompt:**
```text
Write eval/run_eval.py using eval/metrics.py: for each question in eval/questions.json run retrieval (K=3 and K=5) and RAG; compute Precision@K, Recall@K, MRR, mean similarity of correct hits, answer correctness (key-fact check against expected_answer, plus an optional manual-review column), grounding (does every cited label map to a retrieved chunk; refusal correctness on unanswerable questions), and performance (retrieval latency, generation latency, end-to-end latency, indexing time from Step 4.3, Gemini token usage, and estimated API cost per query using a dated official pricing source). Save raw per-question results to eval/results/results.csv and summary to eval/results/summary.json. Explain in the output which suggested metrics you excluded and why.
```
**Tests:** metric unit tests with hand-computed values; a runner test on a tiny set with a stub LLM.
**Done when:** results files are produced from the real system.

#### Step 9.2 — Four cases and error analysis
**Goal:** honest, specific failure analysis.
**Codex prompt:**
```text
Write docs/EVALUATION.md containing: setup (corpus, model names, chunk config, K), the metric tables, and the four REQUIRED cases with real examples pulled from results.csv: (1) correct chunk retrieved (query, chunk, score), (2) wrong chunk retrieved (why it scored highly, what it shared with the query), (3) multiple relevant chunks retrieved (how they were ranked and combined), (4) insufficient information (declined correctly, or hallucinated). Then an error-analysis section covering EVERY failure mode you actually observed (incorrect retrieval, irrelevant chunks, poor chunk boundaries, missing context, hallucinated answers, ambiguous questions, duplicate content, long-context issues), each with: the question, what was retrieved, what the system answered, why it failed, and the fix you would apply (or applied). Include limitations that you could not fix. Do not invent failures; if a failure mode did not occur, say it was not observed.
```
**Tests:** a test that checks the document contains all required section headings.
**Done when:** document written from real data.

#### Step 9.3 — Optional improvement pass (only if time and user agrees)
**Goal:** act on the top 1-2 findings (e.g. tune K/threshold, add neighbour-chunk retrieval or a prompt fix), re-run the evaluation, and add a before/after table to `EVALUATION.md`. Skip if the user does not want it.

---

### PHASE 10 — Documentation and Delivery (Module M10, DEV)

#### Step 10.1 — README and architecture
**Codex prompt:**
```text
Write the README.md with these 13 sections in this order: 1 Project Overview, 2 Business Problem, 3 Features, 4 Architecture (embed the mermaid diagram from docs/architecture.md showing both pipelines and the vector DB), 5 Technology Stack (with a "why this choice / what I compared it against" note for ChromaDB vs FAISS, MiniLM vs alternatives, Gemini vs other hosted/local API options, Gradio+FastAPI), 6 Installation (clone, venv, requirements, Google AI Studio API key setup), 7 Configuration (every env variable explained, .env.example), 8 Usage (run backend, run frontend, workflow), 9 Example Queries (from docs/SEARCH_EXAMPLES.md), 10 Evaluation (summary tables, link to docs/EVALUATION.md, chunking decision with evidence), 11 Screenshots, 12 Limitations, 13 Future Improvements. Use the project name and logo at the top. Everything stated must match what the code actually does.
```
**Tests:** a test checking README has the 13 headings and that every env var in `.env.example` is documented.
**Done when:** README complete and consistent.

#### Step 10.2 — Screenshots, security check, fresh-clone test, caption  *(EXTERNAL parts)*
**Codex prompt:**
```text
(1) Screenshots: capture UI screenshots into docs/screenshots/ (documents tab with indexed docs, indexing progress, search results with scores, an answer with sources, a refusal, empty state) via Playwright if possible; otherwise give the user an EXTERNAL ACTION REQUIRED list of exactly which screenshots to take and filenames. (2) Security: grep the repo and git history for secrets, confirm .env is ignored, .env.example has names only, and no private documents are committed. (3) Fresh-clone test: in a temp folder, clone the repo, follow README instructions literally in a new venv, start backend and frontend, index the sample docs and ask a question; fix any README gaps. (4) Write docs/LINKEDIN_CAPTION.md: lead with the problem, then solution, technologies, key features, what was learned, what would be improved next, and a tag for seKer AI. Also list the 8 things the LinkedIn video must show (UI, upload, indexing, semantic search, natural-language question, retrieved context, AI answer, sources) as a recording script with timings (2-4 minutes). (5) Ask the user for the GitHub remote URL (EXTERNAL) and give steps to create a public repo and push; do not push without their go-ahead.
```
**Tests:** a test or script that fails if `.env` is tracked or if obvious key patterns appear in tracked files.
**Done when:** fresh clone runs cleanly; caption and recording script written.

---

### PHASE 11 — Final Audit

#### Step 11.1 — Ground-truth audit (LAST STEP)
**Codex prompt:**
```text
Open GROUND_TRUTH.md and audit the finished project item by item. For each checkbox: verify it against the actual code, tests, docs and running app (do not tick from memory); tick it with `[x]` and append a short evidence reference (file path or test name), or leave it `[ ]` and add a note on what is missing. Items tagged [USER] (LinkedIn video/post, certificate name, submission) cannot be completed by you: list them clearly for the user. Then fix every gap you can (implement missing items, add missing tests, update docs), re-run the full test suite (`pytest`) including `gemini` tests when configured, and re-audit until every non-[USER] item is ticked. Finally write an "AUDIT RESULT" section at the top of PROGRESS.md: totals, remaining [USER] items, known limitations, and the exact commands to run the project and the tests. Do not tick anything you have not verified.
```
**Done when:** all non-[USER] items are ticked with evidence, the full suite passes, and `PROGRESS.md` has the AUDIT RESULT.

---

## 11. After Phase 11 (optional, only if the user asks)
Advanced extras from the brief (pick at most 2-3): hybrid keyword + semantic search, reranking, chat history with follow-ups, OCR for scanned PDFs, evaluation dashboard, domain specialisation. Add them as new steps in `PROGRESS.md` and extend `GROUND_TRUTH.md` accordingly.
