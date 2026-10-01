"""Stage 1 - Ingest: store the uploaded document by hash and extract its text."""
import hashlib
import io
from dataclasses import dataclass
from pathlib import Path

from ..config import VAR_DIR

SUPPORTED = {".pdf", ".docx", ".txt"}


class UnsupportedDocument(ValueError):
    pass


@dataclass
class IngestedDocument:
    name: str
    sha256: str
    kind: str
    text: str
    pages: int
    ocr_pages: list[int]
    warnings: list[str]


def store(data: bytes, suffix: str) -> str:
    digest = hashlib.sha256(data).hexdigest()
    folder = VAR_DIR / "documents"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{digest}{suffix}"
    if not path.exists():
        path.write_bytes(data)
    return digest


def _extract_pdf(data: bytes) -> tuple[str, int, list[int], list[str]]:
    import pymupdf as fitz

    texts, ocr_pages, warnings = [], [], []
    with fitz.open(stream=data, filetype="pdf") as doc:
        for i, page in enumerate(doc, start=1):
            t = page.get_text("text")
            if len(t.strip()) < 20:
                ocr_pages.append(i)
                t = _ocr_page(page, warnings)
            texts.append(t)
        return "\n".join(texts), doc.page_count, ocr_pages, warnings


def _ocr_page(page, warnings: list[str]) -> str:
    """Scanned page: use PaddleOCR when installed, otherwise report it."""
    try:
        from paddleocr import PaddleOCR  # optional dependency
    except ImportError:
        warnings.append(f"Page {page.number + 1} looks scanned; install PaddleOCR to read it.")
        return ""
    import numpy as np

    pix = page.get_pixmap(dpi=200)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    result = PaddleOCR(lang="en").ocr(img)
    return "\n".join(line[1][0] for block in result or [] for line in block or [])


def _extract_docx(data: bytes) -> str:
    import docx

    d = docx.Document(io.BytesIO(data))
    parts = [p.text for p in d.paragraphs]
    for table in d.tables:
        for row in table.rows:
            parts.append(" | ".join(c.text.strip() for c in row.cells))
    return "\n".join(parts)


def ingest(name: str, data: bytes) -> IngestedDocument:
    suffix = Path(name).suffix.lower()
    if suffix not in SUPPORTED:
        raise UnsupportedDocument(f"Unsupported file type '{suffix}'. Use PDF, DOCX or TXT.")
    digest = store(data, suffix)
    pages, ocr_pages, warnings = 1, [], []
    if suffix == ".pdf":
        text, pages, ocr_pages, warnings = _extract_pdf(data)
    elif suffix == ".docx":
        text = _extract_docx(data)
    else:
        text = data.decode("utf-8", errors="replace")
    return IngestedDocument(name, digest, suffix[1:], text, pages, ocr_pages, warnings)
