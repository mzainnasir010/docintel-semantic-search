# Quillseek REST API

Start the backend with:

```powershell
Remove-Item Env:GEMINI_API_KEY -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe scripts/run_backend.py
```

The server uses `API_HOST` and `API_PORT` from `.env` (defaults: `127.0.0.1:8000`). Interactive OpenAPI docs are available at `/docs`; the JSON schema is at `/openapi.json`.

## Health

```http
GET /health
```

Returns API status, whether Gemini is configured and its model metadata endpoint is reachable, embedding model, and indexed chunk count. Example:

```json
{
  "status": "ok",
  "gemini_configured": true,
  "gemini_reachable": true,
  "gemini_model": "gemini-3.8-flash",
  "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
  "chunk_count": 238
}
```

## Upload and list documents

Upload one or more PDF, DOCX, or TXT files as multipart field `files`. Filenames are sanitized, uploads are size-limited by `MAX_UPLOAD_BYTES`, and files remain pending until indexed.

```powershell
curl.exe -F "files=@manual.pdf" -F "files=@notes.txt" http://127.0.0.1:8000/documents/upload
```

```http
GET /documents
```

The response contains indexed document summaries (`doc_id`, name, chunk count, pages) and pending upload filenames.

Delete indexed content and any matching pending upload by its content-derived document ID:

```http
DELETE /documents/{doc_id}
```

## Index uploads

Indexing runs in a background worker. The POST responds with HTTP 202 and a job ID:

```http
POST /index
```

```json
{"job_id":"<job-id>","indexed":0,"skipped":0,"failed":[],"chunks_indexed":0,"finished":false}
```

Poll for progress, counts, errors, and completion:

```http
GET /index/status/{job_id}
```

Only one index job per API application/collection runs at a time. A concurrent `POST /index`, or a collection reset during indexing, returns HTTP 409.

## Search and ask

Both routes accept JSON with a nonblank `query` and optional `k` from 1 to 100.

```http
POST /search
Content-Type: application/json

{"query":"How does asyncio support asynchronous I/O?","k":5}
```

Search returns ranked chunks with their similarity and source metadata, without calling Gemini.

```http
POST /ask
Content-Type: application/json

{"query":"What syntax does asyncio use for concurrency?","k":5}
```

Ask returns a context-grounded answer, inline source labels, source snippets and metadata, retrieved chunks, retrieval/generation milliseconds, and a refusal flag. If no result meets `MIN_SIMILARITY`, the service returns `the answer is not present in the supplied documents` without calling Gemini.

## Reset collection and uploads

```http
DELETE /collection
```

Deletes indexed chunks and pending uploads. The route returns HTTP 409 while an indexing job is active.

Errors use a consistent shape without stack traces:

```json
{"error":"request_error","detail":"Document not found"}
```
