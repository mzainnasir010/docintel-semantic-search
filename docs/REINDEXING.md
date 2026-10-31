# Re-index after changing the embedding model

ChromaDB records which embedding model created a collection and rejects a different model at startup. Rebuild the vector index whenever `EMBEDDING_MODEL` changes.

1. Stop the backend and frontend processes.
2. Keep the original documents in `data/uploads/` and `data/sample_docs/`; back up any other source files that are not stored elsewhere.
3. Delete only the persisted index directory configured by `CHROMA_PATH` (default: `data/chroma/`). This removes vectors and metadata, not the source documents.
4. Set the new `EMBEDDING_MODEL` in the project-root `.env`.
5. Start the backend and frontend using the README commands. The backend creates a fresh collection using the new model.
6. In **Documents**, index pending uploads. To rebuild the bundled corpus, run `python backend/scripts/index_corpus.py` from the project root.
7. Confirm the indexed chunk count in the UI or `/health`, then run a known semantic search query.

Do not change the model while the old Chroma collection still exists: the model-mismatch guard intentionally prevents mixing vectors from different embedding spaces.
