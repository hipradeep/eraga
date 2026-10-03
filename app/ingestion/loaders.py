"""Document loaders — turn files into structured text blocks.

Every loader returns `DocumentBlock` records so page/section provenance survives
all the way into the stored chunks and, ultimately, into the answer's citations.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SUPPORTED_TYPES = ("pdf", "docx", "html", "htm", "txt", "md", "markdown")


@dataclass(slots=True)
class DocumentBlock:
    text: str
    page_number: int | None = None
    section: str | None = None


def load_pdf(path: str | Path) -> list[DocumentBlock]:
    """PyMuPDF: page-accurate text extraction."""
    import pymupdf

    blocks: list[DocumentBlock] = []
    with pymupdf.open(path) as doc:
        for page_no, page in enumerate(doc, start=1):
            text = page.get_text("text").strip()
            if text:
                blocks.append(DocumentBlock(text=text, page_number=page_no))
    return blocks


def load_docx(path: str | Path) -> list[DocumentBlock]:
    """python-docx: paragraphs plus heading detection for section labels."""
    import docx

    document = docx.Document(str(path))
    blocks: list[DocumentBlock] = []
    current_section: str | None = None
    buffer: list[str] = []

    def flush() -> None:
        if buffer:
            joined = "\n".join(buffer).strip()
            if joined:
                blocks.append(DocumentBlock(text=joined, section=current_section))
            buffer.clear()

    for para in document.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        style = (para.style.name or "").lower() if para.style is not None else ""
        if style.startswith("heading"):
            flush()
            current_section = text
        else:
            buffer.append(text)
    flush()
    return blocks


def load_html(path: str | Path) -> list[DocumentBlock]:
    """BeautifulSoup: drop script/style, keep h1-h6 as section markers."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(Path(path).read_text(encoding="utf-8", errors="ignore"), "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    blocks: list[DocumentBlock] = []
    current_section: str | None = None
    buffer: list[str] = []

    def flush() -> None:
        if buffer:
            joined = "\n".join(buffer).strip()
            if joined:
                blocks.append(DocumentBlock(text=joined, section=current_section))
            buffer.clear()

    heading_names = {"h1", "h2", "h3", "h4", "h5", "h6"}
    for element in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "td", "pre"]):
        text = element.get_text(" ", strip=True)
        if not text:
            continue
        if element.name in heading_names:
            flush()
            current_section = text
        else:
            buffer.append(text)
    flush()
    return blocks or [DocumentBlock(text=soup.get_text("\n").strip())]


def load_txt(path: str | Path) -> list[DocumentBlock]:
    return [DocumentBlock(text=Path(path).read_text(encoding="utf-8", errors="ignore"))]


def load_markdown(path: str | Path) -> list[DocumentBlock]:
    text = Path(path).read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()
    blocks: list[DocumentBlock] = []
    current_section: str | None = None
    buffer: list[str] = []

    def flush() -> None:
        if buffer:
            joined = "\n".join(buffer).strip()
            if joined:
                blocks.append(DocumentBlock(text=joined, section=current_section))
            buffer.clear()

    for line in lines:
        match = re.match(r"^(#{1,6})\s+(.*)$", line)
        if match:
            flush()
            current_section = match.group(2).strip()
        else:
            buffer.append(line)
    flush()
    return blocks


LOADERS: dict[str, Any] = {
    "pdf": load_pdf,
    "docx": load_docx,
    "html": load_html,
    "htm": load_html,
    "txt": load_txt,
    "md": load_markdown,
    "markdown": load_markdown,
}


def detect_doc_type(path: str | Path) -> str:
    return Path(path).suffix.lstrip(".").lower()


def load(path: str | Path, doc_type: str | None = None) -> list[DocumentBlock]:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"no such file: {path}")

    resolved = (doc_type or detect_doc_type(path)).lower()
    loader = LOADERS.get(resolved)
    if loader is None:
        raise ValueError(
            f"unsupported document type '{resolved}'; supported: {', '.join(SUPPORTED_TYPES)}"
        )

    blocks = loader(path)
    blocks = [block for block in blocks if block.text.strip()]
    if not blocks:
        raise ValueError(f"no text extracted from {path.name} (scanned image or empty file?)")
    return blocks
