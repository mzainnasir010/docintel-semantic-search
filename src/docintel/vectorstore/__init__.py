"""Persistent ChromaDB vector storage."""

from docintel.vectorstore.store import ChromaVectorStore, EmbeddingModelMismatchError

__all__ = ["ChromaVectorStore", "EmbeddingModelMismatchError"]
