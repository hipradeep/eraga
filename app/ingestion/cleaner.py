"""Text normalisation applied before chunking.

Removes PDF artefacts (page headers/footers, hyphenation, repeated whitespace) that
otherwise pollute the BM25 index and confuse the embedding model.
"""

import re

_WHITESPACE = re.compile(r"[ \t   ]+")
_MULTI_NEWLINE = re.compile(r"\n{3,}")
_MULTI_SPACE = re.compile(r" {2,}")
_HYPHEN_BREAK = re.compile(r"(\w)-\n(\w)")
_PAGE_ARTIFACT = re.compile(r"^\s*(page\s+\d+(\s+of\s+\d+)?|\d+)\s*$", re.IGNORECASE)
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _dedupe_repeated_lines(text: str) -> str:
    """Drop consecutive duplicate lines (classic PDF running-header artefact)."""
    out: list[str] = []
    previous: str | None = None
    for line in text.split("\n"):
        stripped = line.strip()
        if _PAGE_ARTIFACT.match(stripped):
            continue
        if stripped == previous:
            continue
        out.append(line)
        previous = stripped
    return "\n".join(out)


def clean(text: str) -> str:
    if not text:
        return ""
    text = _CONTROL.sub("", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _HYPHEN_BREAK.sub(r"\1\2", text)
    text = _WHITESPACE.sub(" ", text)
    text = _MULTI_SPACE.sub(" ", text)
    text = _dedupe_repeated_lines(text)
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    text = _MULTI_NEWLINE.sub("\n\n", text)
    return text.strip()


def clean_blocks(blocks: list) -> list:
    """Return new blocks with cleaned text, dropping blocks that become empty."""
    from app.ingestion.loaders import DocumentBlock

    cleaned = [
        DocumentBlock(
            text=clean(block.text),
            page_number=block.page_number,
            section=block.section,
        )
        for block in blocks
    ]
    return [block for block in cleaned if block.text]
