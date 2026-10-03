"""Structure-aware chunking.

Splits on semantic boundaries first (headings / sections), then falls back to a
recursive character splitter inside each section. Preserves `page_number` and
`section` on every chunk so citations stay traceable.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from langchain_text_splitters import RecursiveCharacterTextSplitter

SEPARATORS = ["\n## ", "\n### ", "\n#### ", "\n\n", "\n", ". ", " ", ""]


@dataclass(slots=True)
class Chunk:
    content: str
    page_number: int | None = None
    section: str | None = None

    @property
    def char_count(self) -> int:
        return len(self.content)

    def as_dict(self) -> dict[str, Any]:
        return {
            "content": self.content,
            "page_number": self.page_number,
            "section": self.section,
            "char_count": self.char_count,
        }


def _make_splitter(chunk_size: int, chunk_overlap: int) -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=SEPARATORS,
        length_function=len,
        keep_separator=True,
    )


def chunk_blocks(
    blocks: Iterable[Any],
    chunk_size: int = 900,
    chunk_overlap: int = 120,
    min_chunk_chars: int = 40,
) -> list[Chunk]:
    """Convert loader blocks into embeddable chunks.

    Args:
        blocks: `DocumentBlock` instances from `app.ingestion.loaders`.
        chunk_size: target characters per chunk.
        chunk_overlap: overlap between consecutive chunks, preserves context.
        min_chunk_chars: drop trailing fragments smaller than this (page numbers etc).
    """
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    splitter = _make_splitter(chunk_size, chunk_overlap)
    chunks: list[Chunk] = []

    for block in blocks:
        text = block.text.strip()
        if not text:
            continue
        for piece in splitter.split_text(text):
            content = piece.strip()
            if len(content) < min_chunk_chars:
                continue
            chunks.append(
                Chunk(
                    content=content,
                    page_number=block.page_number,
                    section=block.section,
                )
            )

    return chunks


def chunk_to_dicts(chunks: Iterable[Chunk]) -> list[dict[str, Any]]:
    return [chunk.as_dict() for chunk in chunks]
