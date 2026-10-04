"""Evidence snapshots: a picture of where each tender item sits in the original PDF.

Each item is located by searching the page for its first line. The crop runs from that line to
the next item (or the page end). Cited IS numbers are highlighted green when they are fine and
red when a finding is raised against them; words that matched the standard are highlighted yellow.
If an item cannot be found (scanned page, text broken across lines) it gets no snapshot and the UI
falls back to the text excerpt.
"""
import logging

from ..citations import find_citations
from ..config import VAR_DIR
from .ingest import stored_path

log = logging.getLogger("isre.evidence")
SNAPSHOTS = VAR_DIR / "snapshots"
GREEN, RED, YELLOW = (0.55, 0.88, 0.55), (1.0, 0.62, 0.62), (1.0, 0.92, 0.45)
MARGIN, PAD, MAX_HEIGHT, DPI = 28, 10, 300, 170


def _anchor(doc, title: str, start_page: int, min_y: float):
    """First match of the item's opening words at or after (start_page, min_y)."""
    needle = " ".join(title.split()[:7])[:48]
    if len(needle) < 4:
        return None
    for pno in range(start_page, doc.page_count):
        for rect in doc[pno].search_for(needle):
            if pno > start_page or rect.y0 >= min_y - 1:
                return pno, rect
    return None


def _mark(page, needle: str, clip, color) -> int:
    rects = page.search_for(needle, clip=clip)[:3]
    for r in rects:
        annot = page.add_highlight_annot(r)
        annot.set_colors(stroke=color)
        annot.update()
    return len(rects)


def pdf_snapshots(sha256: str, items: list[dict]) -> dict[int, dict]:
    """item index -> {"image": url, "page": n, "highlights": k}. Never raises."""
    try:
        import pymupdf
    except ImportError:
        return {}
    path = stored_path(sha256, "pdf")
    if not path.exists() or not items:
        return {}
    out: dict[int, dict] = {}
    try:
        SNAPSHOTS.mkdir(parents=True, exist_ok=True)
        with pymupdf.open(path) as doc:
            anchors, page_no, y = {}, 0, 0.0
            for it in items:
                hit = _anchor(doc, it["title"], page_no, y)
                if hit:
                    anchors[it["index"]] = hit
                    page_no, y = hit[0], hit[1].y1
            ordered = [anchors.get(it["index"]) for it in items]
            for n, it in enumerate(items):
                if not ordered[n]:
                    continue
                pno, rect = ordered[n]
                page = doc[pno]
                nxt = next((a for a in ordered[n + 1:] if a), None)
                bottom = nxt[1].y0 - 4 if nxt and nxt[0] == pno else page.rect.y1 - MARGIN
                top = max(page.rect.y0, rect.y0 - PAD)
                clip = pymupdf.Rect(page.rect.x0 + MARGIN, top, page.rect.x1 - MARGIN,
                                    min(bottom, top + MAX_HEIGHT))
                words = page.get_text("words", clip=clip)
                if words:  # shrink to the text so a one-line item isn't a thin page-wide strip
                    clip = pymupdf.Rect(max(page.rect.x0, min(w[0] for w in words) - PAD), clip.y0,
                                        min(page.rect.x1, max(w[2] for w in words) + PAD),
                                        min(clip.y1, max(w[3] for w in words) + PAD))
                flagged = {f.get("citation") for f in it["findings"] if f.get("citation")}
                marks = 0
                for c in find_citations(it["text"]):
                    marks += _mark(page, c.raw, clip, RED if c.raw in flagged else GREEN)
                for term in it.get("matched_terms", [])[:6]:
                    if len(term) >= 3:
                        marks += _mark(page, term, clip, YELLOW)
                name = f"{sha256[:16]}-{it['index']}.png"
                page.get_pixmap(clip=clip, dpi=DPI).save(SNAPSHOTS / name)
                while page.first_annot:  # clear before the next item on the same page
                    page.delete_annot(page.first_annot)
                out[it["index"]] = {"image": f"/api/snapshots/{name}", "page": pno + 1, "highlights": marks}
    except Exception:  # a snapshot is a nice-to-have; the health check must still return
        log.exception("Snapshot rendering failed for %s", sha256[:12])
    return out
