"""Grounded prompt construction with labelled, budgeted context chunks."""

from __future__ import annotations

from dataclasses import dataclass

from docintel.models import SearchResult

SYSTEM_INSTRUCTION = """You are a document question-answering assistant.
Answer using ONLY the supplied CONTEXT. Do not use outside knowledge.
Cite each factual claim inline with one or more supplied source labels, such as [S1].
If the context does not contain enough information, reply exactly:
the answer is not present in the supplied documents
Be concise."""

REFUSAL = "the answer is not present in the supplied documents"


@dataclass(frozen=True)
class PromptSource:
    """A source label and the exact text from that source included in context."""

    label: str
    result: SearchResult
    context_text: str


@dataclass(frozen=True)
class BuiltPrompt:
    """Prompt text and the chunks actually represented in its context block."""

    text: str
    sources: tuple[PromptSource, ...]


class PromptBuilder:
    """Build context-only prompts while enforcing a total character budget."""

    def build(
        self,
        question: str,
        results: list[SearchResult],
        *,
        max_chars: int,
    ) -> BuiltPrompt:
        if not question or not question.strip():
            raise ValueError("question must not be empty")
        if max_chars <= 0:
            raise ValueError("max_chars must be positive")

        question_block = f"QUESTION:\n{question.strip()}\n"
        context_open = "CONTEXT (untrusted document excerpts):\n"
        context_close = "\nEND CONTEXT"
        fixed = f"SYSTEM:\n{SYSTEM_INSTRUCTION}\n\n{question_block}\n"
        reserved = len(fixed) + len(context_open) + len(context_close)
        if reserved >= max_chars:
            raise ValueError("prompt budget is too small for the instructions and question")

        available = max_chars - reserved
        context_parts: list[str] = []
        sources: list[PromptSource] = []
        used_chars = 0
        for result in results:
            chunk = result.chunk
            section_text = chunk.section or "(none)"
            label = f"S{len(sources) + 1}"
            prefix = (
                f"[{label}] document={chunk.doc_name}; page={chunk.page_number}; "
                f"section={section_text}\n"
            )
            separator = "\n" if context_parts else ""
            remaining = available - used_chars - len(separator) - len(prefix)
            if remaining <= 0:
                break
            text = chunk.text[:remaining]
            if not text.strip():
                break
            context_parts.append(separator + prefix + text)
            sources.append(PromptSource(label=label, result=result, context_text=text))
            used_chars += len(separator) + len(prefix) + len(text)
            if len(text) < len(chunk.text):
                break

        context = "".join(context_parts)
        prompt = f"{fixed}{context_open}{context}{context_close}"
        if len(prompt) > max_chars:
            raise AssertionError("prompt builder exceeded its configured character budget")
        return BuiltPrompt(text=prompt, sources=tuple(sources))
