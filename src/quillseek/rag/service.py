"""Grounded RAG orchestration over semantic retrieval and an LLM interface."""

from __future__ import annotations

import re
import time
from collections.abc import Iterable

from pydantic import BaseModel, Field

from quillseek.config import get_settings
from quillseek.models import SearchResponse, SearchResult
from quillseek.rag.llm import LLMClient
from quillseek.rag.prompt import REFUSAL, PromptBuilder
from quillseek.search import SearchService


class CitationValidationError(ValueError):
    """The model answer cites an unknown source or has no source citations."""


class RAGSource(BaseModel):
    """Source details made available to cite in a generated answer."""

    label: str
    doc_name: str
    page_number: int
    section: str | None
    similarity: float
    snippet: str


class RAGResponse(BaseModel):
    """Answer, cited sources, retrieval evidence, and stage timings."""

    answer: str
    sources: list[RAGSource] = Field(default_factory=list)
    retrieved_chunks: list[SearchResult] = Field(default_factory=list)
    retrieval_ms: float = Field(ge=0.0)
    generation_ms: float = Field(ge=0.0)
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    refused: bool


class RAGService:
    """Retrieve evidence and generate a concise, source-validated answer."""

    _CITATION_PATTERN = re.compile(r"\[(S[^\]]*)\]")
    SNIPPET_CHARS = 500

    def __init__(
        self,
        search_service: SearchService | None = None,
        llm_client: LLMClient | None = None,
        prompt_builder: PromptBuilder | None = None,
        *,
        context_budget: int | None = None,
    ) -> None:
        self.search_service = search_service or SearchService()
        if llm_client is None:
            from quillseek.rag.llm import GeminiClient

            llm_client = GeminiClient()
        self.llm_client = llm_client
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.context_budget = (
            get_settings().rag_prompt_char_budget
            if context_budget is None
            else context_budget
        )

    def retrieve(self, question: str, k: int | None = None) -> SearchResponse:
        """Retrieval-only mode for the Search tab; this never calls the LLM."""
        return self.search_service.search(question, k=k)

    def ask(self, question: str, k: int | None = None) -> RAGResponse:
        """Answer from retrieved documents, or return the exact honest refusal."""
        started = time.perf_counter()
        search_response = self.search_service.search(question, k=k)
        retrieval_ms = (time.perf_counter() - started) * 1000.0
        retrieved = search_response.results
        if not search_response.is_relevant or not retrieved:
            return RAGResponse(
                answer=REFUSAL,
                sources=[],
                retrieved_chunks=[],
                retrieval_ms=retrieval_ms,
                generation_ms=0.0,
                refused=True,
            )

        built = self.prompt_builder.build(
            question, retrieved, max_chars=self.context_budget
        )
        generation_started = time.perf_counter()
        raw_answer = self.llm_client.generate(built.text)
        generation_ms = (time.perf_counter() - generation_started) * 1000.0
        usage = getattr(self.llm_client, "last_usage", None)
        token_fields = {
            "input_tokens": usage.get("input_tokens") if usage else None,
            "output_tokens": usage.get("output_tokens") if usage else None,
            "total_tokens": usage.get("total_tokens") if usage else None,
        }
        answer = raw_answer.strip()
        if answer.casefold() == REFUSAL:
            return RAGResponse(
                answer=REFUSAL,
                sources=[],
                retrieved_chunks=retrieved,
                retrieval_ms=retrieval_ms,
                generation_ms=generation_ms,
                **token_fields,
                refused=True,
            )

        sources = self._validated_sources(answer, built.sources)
        return RAGResponse(
            answer=answer,
            sources=sources,
            retrieved_chunks=retrieved,
            retrieval_ms=retrieval_ms,
            generation_ms=generation_ms,
            **token_fields,
            refused=False,
        )

    def _validated_sources(self, answer: str, available: Iterable) -> list[RAGSource]:
        by_label = {source.label: source for source in available}
        citations = self._CITATION_PATTERN.findall(answer)
        if not citations:
            raise CitationValidationError("The answer must cite at least one source label.")
        unknown = sorted(set(citations) - by_label.keys())
        if unknown:
            raise CitationValidationError(
                "The answer cited unknown source label(s): " + ", ".join(unknown)
            )
        used_labels = set(citations)
        result: list[RAGSource] = []
        for label, source in by_label.items():
            if label not in used_labels:
                continue
            chunk = source.result.chunk
            result.append(
                RAGSource(
                    label=label,
                    doc_name=chunk.doc_name,
                    page_number=chunk.page_number,
                    section=chunk.section,
                    similarity=source.result.similarity,
                    snippet=source.context_text[: self.SNIPPET_CHARS],
                )
            )
        return result
