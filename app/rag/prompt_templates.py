SYSTEM_PROMPT = """You are ERAGA, an enterprise knowledge assistant.

Rules:
1. Answer ONLY from the supplied CONTEXT. Treat it as the only source of truth.
2. Never invent, extrapolate, or fall back on prior knowledge.
3. Cite every claim inline using the bracketed source markers, e.g. [1] or [2].
4. If the context does not contain the answer, reply exactly:
   I don't have enough information to answer this.
5. Be concise and factual. Use markdown lists only when they aid clarity.
"""

USER_TEMPLATE = """CONTEXT:
{context}

QUESTION:
{question}

ANSWER (cite sources inline as [1], [2]):"""

NO_CONTEXT_ANSWER = "I don't have enough information to answer this."


def format_context(chunks: list) -> str:
    """Render retrieved chunks as a numbered, citable context block."""
    blocks: list[str] = []
    for index, item in enumerate(chunks, start=1):
        chunk = item.chunk if hasattr(item, "chunk") else item
        source = (getattr(chunk, "extra_metadata", None) or {}).get("source") or "document"
        location = f"section {chunk.section}" if chunk.section else "unsectioned"
        page = f", page {chunk.page_number}" if chunk.page_number else ""
        blocks.append(f"[{index}] Source: {source} ({location}{page})\n{chunk.content}")
    return "\n\n".join(blocks)


def build_prompt(question: str, chunks: list) -> str:
    return USER_TEMPLATE.format(context=format_context(chunks), question=question)


def build_messages(question: str, chunks: list, history: list[dict] | None = None) -> list[tuple]:
    messages: list[tuple] = [("system", SYSTEM_PROMPT)]
    for turn in (history or [])[-4:]:
        messages.append(("human", turn.get("question", "")))
        messages.append(("ai", turn.get("answer", "")))
    messages.append(("human", build_prompt(question, chunks)))
    return messages
