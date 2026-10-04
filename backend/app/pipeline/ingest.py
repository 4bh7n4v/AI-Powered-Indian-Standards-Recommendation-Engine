"""Stage 1 - Ingest: store the uploaded document by hash and extract its text."""
import hashlib
import io
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlparse

from ..config import MAX_UPLOAD_BYTES, URL_FETCH_TIMEOUT, VAR_DIR

SUPPORTED = {".pdf", ".docx", ".pptx", ".txt", ".html", ".htm"}
DOCUMENTS = VAR_DIR / "documents"


class UnsupportedDocument(ValueError):
    pass


class FetchError(ValueError):
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
    DOCUMENTS.mkdir(parents=True, exist_ok=True)
    path = DOCUMENTS / f"{digest}{suffix}"
    if not path.exists():
        path.write_bytes(data)
    return digest


def stored_path(sha256: str, kind: str) -> Path:
    return DOCUMENTS / f"{sha256}.{kind}"


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


def _extract_pptx(data: bytes) -> tuple[str, int]:
    """Slide text in reading order: text boxes, then table rows; a blank line between slides."""
    from pptx import Presentation

    prs = Presentation(io.BytesIO(data))
    parts = []
    for slide in prs.slides:
        for shape in slide.shapes:
            if shape.has_text_frame:
                parts.extend(p.text for p in shape.text_frame.paragraphs)
            if getattr(shape, "has_table", False) and shape.has_table:
                for row in shape.table.rows:
                    parts.append(" | ".join(c.text.strip() for c in row.cells))
        parts.append("")
    return "\n".join(parts), len(prs.slides)


class _HTMLText(HTMLParser):
    """Readable text from a web page: skips scripts and styles, keeps block breaks."""
    BLOCKS = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "section", "article", "table"}
    SKIP = {"script", "style", "noscript", "template", "svg"}

    def __init__(self):
        super().__init__()
        self.parts: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip += 1
        elif tag in self.BLOCKS:
            self.parts.append("\n")
        elif tag in ("td", "th"):
            self.parts.append(" | ")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.skip:
            self.skip -= 1
        elif tag in self.BLOCKS:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def _extract_html(data: bytes) -> str:
    parser = _HTMLText()
    parser.feed(data.decode("utf-8", errors="replace"))
    lines = (" ".join(line.split()) for line in "".join(parser.parts).splitlines())
    return "\n".join(line.strip(" |") for line in lines if line.strip(" |"))


def ingest(name: str, data: bytes) -> IngestedDocument:
    suffix = Path(name).suffix.lower()
    if suffix not in SUPPORTED:
        raise UnsupportedDocument(f"Unsupported file type '{suffix}'. Use PDF, DOCX, PPTX, TXT or HTML.")
    digest = store(data, suffix)
    pages, ocr_pages, warnings = 1, [], []
    if suffix == ".pdf":
        text, pages, ocr_pages, warnings = _extract_pdf(data)
    elif suffix == ".docx":
        text = _extract_docx(data)
    elif suffix == ".pptx":
        text, pages = _extract_pptx(data)
    elif suffix in (".html", ".htm"):
        text = _extract_html(data)
    else:
        text = data.decode("utf-8", errors="replace")
    return IngestedDocument(name, digest, suffix[1:], text, pages, ocr_pages, warnings)


CONTENT_TYPES = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "text/plain": ".txt",
    "text/html": ".html",
}


def fetch_url(url: str) -> tuple[str, bytes]:
    """Download a tender from a link. Returns a file name whose suffix picks the extractor."""
    import httpx

    if urlparse(url).scheme not in ("http", "https"):
        raise FetchError("Enter a link that starts with http:// or https://.")
    try:
        with httpx.stream("GET", url, follow_redirects=True, timeout=URL_FETCH_TIMEOUT,
                          headers={"User-Agent": "Mozilla/5.0 (IS-Recommendation-Engine)"}) as r:
            if r.status_code >= 400:
                raise FetchError(f"The link returned HTTP {r.status_code}.")
            data = b""
            for chunk in r.iter_bytes():
                data += chunk
                if len(data) > MAX_UPLOAD_BYTES:
                    raise FetchError("The linked file is larger than 10 MB.")
            content_type = r.headers.get("content-type", "").split(";")[0].strip().lower()
            final_url = str(r.url)
    except httpx.HTTPError as exc:
        raise FetchError(f"Could not download the link ({type(exc).__name__}).") from exc

    name = unquote(PurePosixPath(urlparse(final_url).path).name) or "page"
    suffix = Path(name).suffix.lower()
    if data[:5] == b"%PDF-":
        suffix = ".pdf"
    elif suffix not in SUPPORTED:
        suffix = CONTENT_TYPES.get(content_type, ".html")
    return f"{Path(name).stem or 'page'}{suffix}", data
