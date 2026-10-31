"""Persistent Chroma vector store with cosine search and typed metadata."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

import chromadb
import numpy as np
from chromadb.errors import NotFoundError

from quillseek.config import get_settings
from quillseek.models import Chunk, IndexedDocument, SearchResult


class EmbeddingModelMismatchError(ValueError):
    """Raised when a collection was created with a different embedding model."""


class ChromaVectorStore:
    """Manage one persistent cosine-distance collection."""

    def __init__(
        self,
        path: str | Path | None = None,
        collection_name: str | None = None,
        embedding_model_name: str | None = None,
        client: Any | None = None,
    ) -> None:
        settings = get_settings()
        self.path = Path(path if path is not None else settings.chroma_path)
        self.collection_name = collection_name or settings.collection_name
        self.embedding_model_name = embedding_model_name or settings.embedding_model
        self.client = client or chromadb.PersistentClient(path=str(self.path))
        self.collection = self._open_or_create()

    def _open_or_create(self):
        try:
            collection = self.client.get_collection(self.collection_name)
        except NotFoundError:
            collection = self.client.create_collection(
                self.collection_name,
                metadata={
                    "hnsw:space": "cosine",
                    "embedding_model": self.embedding_model_name,
                },
            )
        metadata = collection.metadata or {}
        stored_model = metadata.get("embedding_model")
        if stored_model != self.embedding_model_name:
            raise EmbeddingModelMismatchError(
                f"Collection '{self.collection_name}' uses embedding model "
                f"{stored_model!r}, but the configured model is "
                f"{self.embedding_model_name!r}. Rebuild the collection with the "
                "matching model or select the model used to create it."
            )
        space = metadata.get("hnsw:space")
        if space != "cosine":
            raise ValueError(
                f"Collection '{self.collection_name}' must use cosine distance; "
                f"found {space!r}. Reset and recreate the collection."
            )
        return collection

    @staticmethod
    def _metadata(chunk: Chunk) -> dict[str, Any]:
        metadata: dict[str, Any] = {
            "doc_id": chunk.doc_id,
            "doc_name": chunk.doc_name,
            "chunk_id": chunk.chunk_id,
            "page_number": chunk.page_number,
            "source_path": str(chunk.source_path),
            "ingested_at": chunk.ingested_at.isoformat(),
            "char_start": chunk.char_start,
            "char_end": chunk.char_end,
        }
        if chunk.section is not None:
            metadata["section"] = chunk.section
        return metadata

    @staticmethod
    def _chunk_from_metadata(chunk_id: str, text: str, metadata: dict[str, Any]) -> Chunk:
        return Chunk(
            chunk_id=chunk_id,
            doc_id=metadata["doc_id"],
            doc_name=metadata["doc_name"],
            text=text,
            page_number=int(metadata["page_number"]),
            section=metadata.get("section"),
            source_path=metadata.get("source_path", ""),
            ingested_at=datetime.fromisoformat(metadata["ingested_at"]),
            char_start=int(metadata.get("char_start", 0)),
            char_end=int(metadata.get("char_end", 0)),
        )

    def add_chunks(self, chunks: Sequence[Chunk], embeddings: Sequence[Sequence[float]]) -> None:
        """Upsert chunks by stable ID with their vector and retrieval metadata."""
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must have the same length")
        if not chunks:
            return
        vectors = np.asarray(embeddings, dtype=np.float32)
        if vectors.ndim != 2 or vectors.shape[0] != len(chunks):
            raise ValueError("embeddings must be a 2D matrix with one row per chunk")
        if not np.isfinite(vectors).all():
            raise ValueError("embeddings must contain only finite values")
        self.collection.upsert(
            ids=[chunk.chunk_id for chunk in chunks],
            embeddings=vectors.tolist(),
            documents=[chunk.text for chunk in chunks],
            metadatas=[self._metadata(chunk) for chunk in chunks],
        )

    def query(
        self,
        embedding: Sequence[float],
        k: int = 5,
        *,
        where: dict[str, Any] | None = None,
        doc_id: str | None = None,
    ) -> list[SearchResult]:
        """Return nearest chunks ordered by cosine similarity, optionally filtered."""
        if k < 1:
            raise ValueError("k must be positive")
        vector = np.asarray(embedding, dtype=np.float32)
        if vector.ndim != 1 or not np.isfinite(vector).all():
            raise ValueError("query embedding must be a finite one-dimensional vector")
        if doc_id is not None:
            if where is not None:
                raise ValueError("pass either where or doc_id, not both")
            where = {"doc_id": doc_id}
        result = self.collection.query(
            query_embeddings=[vector.tolist()],
            n_results=k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        return [
            SearchResult(
                chunk=self._chunk_from_metadata(chunk_id, text, metadata),
                similarity=max(-1.0, min(1.0, 1.0 - float(distance))),
                rank=rank,
            )
            for rank, (chunk_id, text, metadata, distance) in enumerate(
                zip(ids, documents, metadatas, distances), start=1
            )
        ]

    def delete_document(self, doc_id: str) -> int:
        """Delete all indexed chunks for one document and return their count."""
        existing = self.collection.get(where={"doc_id": doc_id}, include=["metadatas"])
        ids = existing.get("ids", [])
        if ids:
            self.collection.delete(ids=ids)
        return len(ids)

    def list_documents(self) -> list[IndexedDocument]:
        """Summarize indexed document names, chunk counts, and page numbers."""
        result = self.collection.get(include=["metadatas"])
        grouped: dict[str, dict[str, Any]] = {}
        for metadata in result.get("metadatas", []):
            doc_id = metadata["doc_id"]
            entry = grouped.setdefault(
                doc_id,
                {"doc_id": doc_id, "doc_name": metadata["doc_name"], "chunk_count": 0, "pages": set()},
            )
            entry["chunk_count"] += 1
            entry["pages"].add(int(metadata["page_number"]))
        return [
            IndexedDocument(**{**entry, "pages": sorted(entry["pages"])})
            for entry in sorted(grouped.values(), key=lambda item: item["doc_name"].casefold())
        ]

    def count(self) -> int:
        """Return the number of indexed chunk vectors."""
        return self.collection.count()

    def reset(self) -> None:
        """Delete and recreate the collection with matching cosine metadata."""
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.create_collection(
            self.collection_name,
            metadata={
                "hnsw:space": "cosine",
                "embedding_model": self.embedding_model_name,
            },
        )
