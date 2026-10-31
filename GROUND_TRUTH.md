# GROUND_TRUTH.md — Definition of "Finished"

> seKer AI · AI & ML Internship · Project 05: AI-Powered Document Intelligence & Semantic Search System
> This is the final checklist. Do **not** tick anything while building. Use it in **Step 11.1** (the last step) to compare the finished implementation against this list and find anything that was missed.

## How to use this file (Step 11.1)
1. Go through every item. Verify against the real code, tests, docs and running app.
2. If verified: change `[ ]` to `[x]` and append ` — evidence: <file path or test name>`.
3. If not verified: leave `[ ]`, add ` — MISSING: <what is missing>`, then fix it and re-verify.
4. Items tagged **[USER]** cannot be done by Codex. List them for the user at the end.
5. Finish only when every non-[USER] item is `[x]` and `pytest` (including configured `gemini` tests) is green.

Tags: **[AI]** = AI/ML work · **[DEV]** = software engineering · **[USER]** = only the user can do it.

---

## 0. Locked stack (verify the implementation matches)
- [ ] Python 3.10+ · FastAPI backend · Gradio frontend (talks to backend over HTTP only)
- [ ] ChromaDB persistent vector store, cosine similarity
- [ ] sentence-transformers embedding model, used for both chunks and queries
- [ ] Google Gemini Developer API via REST (`httpx`), API key read from `.env`, swappable behind an interface
- [ ] PyMuPDF + python-docx loaders · LangChain text splitters
- [ ] No model training or fine-tuning anywhere (all pre-trained models used as-is)

---

## M1 — Document Ingestion [DEV]
- [ ] Loaders for PDF, DOCX and TXT
- [ ] Auto-detect file type and route to the correct loader
- [ ] Metadata extracted: file name, page number, section, creation date (where available)
- [ ] Stable document name and ID for every file (idempotent re-ingestion)
- [ ] Multiple documents handled in a single indexing run
- [ ] Per-document error boundary with logging (one bad file never stops the run)
- [ ] Empty or image-only pages handled without crashing
- [ ] Encoding issues and unusual characters handled gracefully
- [ ] Unsupported file types rejected cleanly

## M2 — Text Preprocessing [AI/NLP]
- [ ] Extra whitespace and repeated newlines removed
- [ ] Extraction artefacts and control characters removed
- [ ] Unicode normalisation and standardised quotes/dashes
- [ ] Repeated headers, footers and page numbers removed
- [ ] Structure preserved (headings, paragraphs, lists, tables)
- [ ] Memory-safe processing of long documents
- [ ] Documented, repeatable preprocessing function (with before/after example saved in docs)

## M3 — Chunking [AI]
- [ ] Chunking strategies implemented: recursive, sentence-based, section-aware
- [ ] Chunk size and overlap configurable
- [ ] Experiments run: small / medium / large sizes, no overlap vs modest overlap, strategy comparison
- [ ] Final strategy, size and overlap chosen with evidence (`docs/CHUNKING_EXPERIMENTS.md`)
- [ ] Description of what went wrong with rejected settings (too small / too large / boundary cuts)
- [ ] Every chunk carries complete metadata and a stable chunk ID

## M4 — Embedding Generation [AI]
- [ ] One embedding model used consistently for chunks and queries
- [ ] Batch embedding, normalised vectors
- [ ] Metadata stored with every vector: doc name, chunk ID, page number, section/heading, source path, ingestion timestamp
- [ ] Embedding-model mismatch between index and query detected (clear error)
- [ ] Full re-index procedure documented for when the model changes

## M5 — Vector Database & Semantic Search [AI + DEV]
- [ ] Persistent ChromaDB index that survives restarts [DEV]
- [ ] Embeddings stored with metadata; upsert is idempotent [DEV]
- [ ] Query embedded with the same model [AI]
- [ ] Top-K retrieval ranked by similarity score [AI]
- [ ] Similarity threshold applied to block weak matches [AI]
- [ ] Delete document and reset/clear collection functions [DEV]
- [ ] README table of real example queries: query, retrieved doc + page, similarity, result (Correct / Partial / Weak) — real measured values only

## M6 — RAG Pipeline [AI]
- [ ] Retrieves the most relevant chunks for the question
- [ ] Prompt clearly separates instructions, retrieved context and the user question
- [ ] LLM (Gemini) generates the answer from the context
- [ ] Answer uses only the retrieved context (no outside knowledge)
- [ ] Inline citations (document and page) for claims
- [ ] Replies that the answer is not present in the supplied documents when context is insufficient
- [ ] Refusal path avoids calling the LLM when nothing passes the similarity threshold
- [ ] Context-length budget guarded
- [ ] Grounding and refusal validated on real unanswerable questions with the live model

## M7 — Backend API [DEV]
- [ ] FastAPI routes: health, upload, list documents, delete document, index (job), index status, search, ask, reset collection
- [ ] Input validation (file type, size, empty query, K bounds) and consistent error responses
- [ ] Background indexing with live progress; no concurrent indexing on the same collection
- [ ] Search and ask keep working during indexing
- [ ] Config and secrets from environment variables only
- [ ] Modular structure: ingestion, preprocessing, chunking, embeddings, vectorstore, indexing, search, rag, api, ui
- [ ] API documentation (`docs/api.md` and OpenAPI)

## M8 — User Interface (Gradio) [DEV]
**Required capabilities**
- [ ] Upload documents (multiple, PDF/DOCX/TXT)
- [ ] View uploaded/indexed documents (name, type, pages, chunks, status)
- [ ] Process/index button with visible progress (never a frozen screen)
- [ ] Clear/reset collection (with confirmation)
- [ ] Natural-language question input
- [ ] Semantic search view
- [ ] Retrieved chunks displayed with similarity scores
- [ ] Generated answer displayed
- [ ] Source documents and page/section references displayed
- [ ] Answer visually distinct from its sources
- [ ] Graceful empty state before any document is uploaded
- [ ] Friendly errors when backend or Gemini API is unavailable

**Branding and design**
- [ ] Theme uses exactly Deep Blue `#09318D`, Pure White `#FFFFFF`, Bubblegum Pink `#FD91CC` (plus neutral tints)
- [ ] One simple, unique, one-word project name chosen and used consistently (UI, README, package, docs)
- [ ] Original SVG logo created from the theme colours and shown in the header AND the footer
- [ ] Favicon and page title set
- [ ] Modern design: card layout, rounded corners, soft shadows, hover/focus states, responsive layout
- [ ] Accessible text contrast on all three brand colours
- [ ] Footer includes name, internship credit and privacy note
- [ ] UI contains no business logic (everything through the API client)

## M9 — Evaluation & Error Analysis [AI]
- [ ] Test set of 20–30 questions with known source passages (includes paraphrased, multi-chunk and 4+ unanswerable questions)
- [ ] Metrics reported: Precision@K, Recall@K, MRR, similarity scores (excluded metrics explained)
- [ ] Performance reported: response latency (retrieval / generation / end to end), indexing time, and Gemini API cost per query based on reported token usage and a dated pricing source
- [ ] Case 1 documented: correct chunk retrieved
- [ ] Case 2 documented: wrong chunk retrieved (why it scored high)
- [ ] Case 3 documented: multiple relevant chunks retrieved and combined
- [ ] Case 4 documented: insufficient information (declined vs hallucinated)
- [ ] Error analysis covers every failure mode actually observed, each with question, retrieval, answer, cause and fix
- [ ] Limitations listed honestly, including unsolved problems
- [ ] Results saved in `eval/results/` and written up in `docs/EVALUATION.md`

## M10 — Documentation, GitHub & Delivery [DEV]
- [ ] Corpus of 5–15 public, legally usable documents with `SOURCES.md` (no private or copyrighted-without-permission material)
- [ ] Clean folder structure and `requirements.txt`
- [ ] `.gitignore` includes `.env`, data/chroma, data/uploads
- [ ] `.env.example` lists variable names with no values
- [ ] No secrets or private documents in the repo or git history
- [ ] README has all 13 sections: Overview, Business Problem, Features, Architecture, Technology Stack, Installation, Configuration, Usage, Example Queries, Evaluation, Screenshots, Limitations, Future Improvements
- [ ] Architecture diagram of both pipelines in the README
- [ ] Technology choices justified (what chosen, what compared, why)
- [ ] Screenshots in `docs/screenshots/` (documents, indexing progress, search with scores, answer with sources, refusal, empty state)
- [ ] Fresh-clone test passed: clone, follow README literally, app starts and works
- [ ] LinkedIn caption drafted (problem, solution, tech, features, learning, next steps, seKer AI tag)
- [ ] LinkedIn recording script written (UI, upload, indexing, semantic search, question, retrieved context, answer, sources; 2–4 min)

---

## Testing and process gates
- [ ] Every feature has unit tests; every component connection has integration tests
- [ ] `tests/unit/` and `tests/integration/` exist; `gemini`-marked tests skip gracefully when credentials/network are unavailable
- [ ] Full suite passes: `pytest` (including `pytest -m gemini` when configured)
- [ ] No test was deleted, skipped or weakened to get green
- [ ] `PROGRESS.md` is complete, current, and has a NEXT STEP section plus an AUDIT RESULT section
- [ ] Each step was committed locally with a clear message
- [ ] Backend completed and tested before frontend work began

---

## Deliverables only the user can complete [USER]
- [ ] [USER] Public GitHub repository created and pushed, with complete README
- [ ] [USER] LinkedIn demonstration video recorded (2–4 min) and published, tagging seKer AI
- [ ] [USER] Screenshots collected (if Codex could not automate them)
- [ ] [USER] Full name exactly as it should appear on the certificate
- [ ] [USER] Email and contact information
- [ ] [USER] Official seKer AI submission completed (repo link, LinkedIn link, screenshots, details)

## Optional extras (not required; only if the user asked)
- [ ] Hybrid keyword + semantic search
- [ ] Reranking
- [ ] Chat history and follow-up questions
- [ ] OCR for scanned PDFs
- [ ] Evaluation dashboard
- [ ] Domain specialisation (domain-specific corpus, prompts, UI, test set)
