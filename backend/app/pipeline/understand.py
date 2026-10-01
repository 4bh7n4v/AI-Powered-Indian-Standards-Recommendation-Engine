"""Stage 2 - Understand: split tenders into items, detect language, extract attributes."""
import json
import re
import urllib.request
from dataclasses import dataclass, field

from ..config import OLLAMA_MODEL, OLLAMA_URL

SCRIPTS = {
    "hi": (0x0900, 0x097F),  # Devanagari (Hindi, Marathi, ...)
    "bn": (0x0980, 0x09FF),
    "pa": (0x0A00, 0x0A7F),
    "gu": (0x0A80, 0x0AFF),
    "or": (0x0B00, 0x0B7F),
    "ta": (0x0B80, 0x0BFF),
    "te": (0x0C00, 0x0C7F),
    "kn": (0x0C80, 0x0CFF),
    "ml": (0x0D00, 0x0D7F),
}
LANG_NAMES = {"en": "English", "hi": "Hindi", "bn": "Bengali", "pa": "Punjabi", "gu": "Gujarati",
              "or": "Odia", "ta": "Tamil", "te": "Telugu", "kn": "Kannada", "ml": "Malayalam"}

ITEM_RE = re.compile(r"^\s*(?:item\s*(?:no\.?)?\s*)?(\d{1,3})\s*[\.\):]\s+(\S.*)$", re.IGNORECASE)

MATERIALS = ["stainless steel", "steel", "copper", "aluminium", "aluminum", "upvc", "pvc", "xlpe",
             "polyethylene", "hdpe", "gold", "silver", "led", "concrete", "cast iron"]
QUANTITY_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(sq\.?\s*mm|mm2|mm|litres?|liters?|ltrs?|kv|kw|w|v|a|m|km|carat|kt)\b", re.IGNORECASE)
GRADE_RE = re.compile(r"\b(Fe\s?\d{3}[A-Z]?|E\s?\d{3}|IP\s?\d{2}|\d{2}\s?K)\b")


@dataclass
class SpecItem:
    index: int
    title: str
    text: str
    line_start: int
    line_end: int


@dataclass
class Attributes:
    materials: list[str] = field(default_factory=list)
    quantities: list[str] = field(default_factory=list)
    grades: list[str] = field(default_factory=list)
    product: str | None = None
    source: str = "rules"


def detect_language(text: str) -> str:
    counts = {k: 0 for k in SCRIPTS}
    latin = 0
    for ch in text:
        o = ord(ch)
        if ch.isascii() and ch.isalpha():
            latin += 1
            continue
        for lang, (lo, hi) in SCRIPTS.items():
            if lo <= o <= hi:
                counts[lang] += 1
                break
    lang, n = max(counts.items(), key=lambda kv: kv[1])
    return lang if n > latin * 0.3 and n > 0 else "en"


def split_items(text: str) -> list[SpecItem]:
    """Split a tender into numbered items; fall back to paragraphs."""
    lines = text.splitlines()
    starts = [(i, m) for i, line in enumerate(lines) if (m := ITEM_RE.match(line))]
    items: list[SpecItem] = []
    if starts:
        for n, (i, m) in enumerate(starts):
            end = starts[n + 1][0] if n + 1 < len(starts) else len(lines)
            body = "\n".join(lines[i:end]).strip()
            items.append(SpecItem(len(items) + 1, m.group(2).strip()[:120], body, i + 1, end))
        return items
    block, first = [], 0
    for i, line in enumerate(lines + [""]):
        if line.strip():
            if not block:
                first = i
            block.append(line)
        elif block:
            body = "\n".join(block).strip()
            if len(body) > 25:
                items.append(SpecItem(len(items) + 1, block[0].strip()[:120], body, first + 1, i))
            block = []
    return items


def extract_attributes(text: str) -> Attributes:
    if OLLAMA_MODEL:
        llm = _extract_with_llm(text)
        if llm:
            return llm
    low = text.lower()
    materials = []
    for m in MATERIALS:
        if re.search(rf"\b{re.escape(m)}\b", low) and not any(m in x for x in materials):
            materials.append(m)
    quantities = sorted({f"{v} {u}" for v, u in QUANTITY_RE.findall(text)})
    grades = sorted({g.replace(" ", "") for g in GRADE_RE.findall(text)})
    return Attributes(materials, quantities, grades)


def _extract_with_llm(text: str) -> Attributes | None:
    """Optional: structured extraction with a local model (Qwen2.5 via Ollama)."""
    prompt = (
        "Extract procurement attributes from the text. Reply with JSON only: "
        '{"product": str, "materials": [str], "quantities": [str], "grades": [str]}. '
        "Only include values that appear in the text.\n\nTEXT:\n" + text[:3000]
    )
    body = json.dumps({"model": OLLAMA_MODEL, "prompt": prompt, "format": "json", "stream": False}).encode()
    try:
        req = urllib.request.Request(f"{OLLAMA_URL}/api/generate", body, {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(json.loads(r.read())["response"])
    except Exception:
        return None
    low = text.lower()
    keep = lambda xs: [x for x in xs or [] if isinstance(x, str) and x.lower() in low]  # grounding check
    product = data.get("product") if isinstance(data.get("product"), str) else None
    return Attributes(keep(data.get("materials")), keep(data.get("quantities")), keep(data.get("grades")),
                      product, source=f"llm:{OLLAMA_MODEL}")
