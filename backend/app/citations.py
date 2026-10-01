"""Parse Indian Standard citations such as 'IS 1554 (Part 1):1988' or 'IS: 1786-2008'."""
import re
from dataclasses import dataclass

CITATION_RE = re.compile(
    r"\bIS\s*(?P<iec>/\s*IEC)?\s*[:\-]?\s*(?P<num>\d{2,5})"
    r"(?:\s*\(\s*(?:Part|Pt\.?)\s*(?P<part>\d+)\s*(?:/\s*Sec(?:tion)?\.?\s*(?P<sec>\d+))?\s*\))?"
    r"(?:\s*[:\-]\s*(?P<year>(?:19|20)\d{2}))?",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Citation:
    raw: str
    number: str
    part: str | None
    section: str | None
    year: int | None
    iec: bool
    start: int
    end: int

    @property
    def candidate_ids(self) -> list[str]:
        base = f"IS-IEC-{self.number}" if self.iec else f"IS-{self.number}"
        ids = []
        if self.part and self.section:
            ids.append(f"{base}-P{self.part}-S{self.section}")
        if self.part:
            ids.append(f"{base}-P{self.part}")
        ids.append(base)
        return ids


def find_citations(text: str) -> list[Citation]:
    out = []
    for m in CITATION_RE.finditer(text):
        out.append(Citation(
            raw=m.group(0).strip(),
            number=m.group("num"),
            part=m.group("part"),
            section=m.group("sec"),
            year=int(m.group("year")) if m.group("year") else None,
            iec=bool(m.group("iec")),
            start=m.start(),
            end=m.end(),
        ))
    return out
