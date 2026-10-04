import type { ReactNode } from "react";

const CITATION_RE = /\bIS\s*(?:\/\s*IEC\s*)?:?\s*\d{2,5}(?:\s*\((?:Part|Pt)[^)]*\))*(?:\s*[:\-–]\s*\d{4})?/gi;
const escape = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

/** Highlight matched words (yellow) in a standard's scope text. */
export function highlightTerms(text: string, terms: string[]): ReactNode {
  if (!terms.length) return text;
  const re = new RegExp(`\\b(${terms.map(escape).join("|")})\\w*`, "gi");
  return text.split(re).map((p, i) => (i % 2 === 1 ? <mark key={i}>{p}</mark> : p));
}

/**
 * Text-excerpt evidence for formats with no page image (DOCX, PPTX, TXT, web pages): IS citations
 * are marked green, or red when a finding names them; matched words are marked yellow.
 */
export function markEvidence(text: string, terms: string[], flagged: Set<string>): ReactNode[] {
  const ranges: { start: number; end: number; cls: string }[] = [];
  for (const m of text.matchAll(CITATION_RE)) {
    const raw = m[0].trim();
    const bad = [...flagged].some((f) => f && (raw.includes(f) || f.includes(raw)));
    ranges.push({ start: m.index!, end: m.index! + m[0].length, cls: bad ? "mark-bad" : "mark-ok" });
  }
  const words = terms.filter((t) => t.length >= 3);
  if (words.length) {
    for (const m of text.matchAll(new RegExp(`\\b(${words.map(escape).join("|")})\\w*`, "gi"))) {
      ranges.push({ start: m.index!, end: m.index! + m[0].length, cls: "mark-term" });
    }
  }
  ranges.sort((a, b) => a.start - b.start);
  const out: ReactNode[] = [];
  let pos = 0;
  for (const r of ranges) {
    if (r.start < pos) continue; // overlapping: the citation found first wins
    if (r.start > pos) out.push(text.slice(pos, r.start));
    out.push(<mark key={r.start} className={r.cls}>{text.slice(r.start, r.end)}</mark>);
    pos = r.end;
  }
  out.push(text.slice(pos));
  return out;
}
