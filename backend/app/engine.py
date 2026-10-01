"""Runs the five stages end to end for a query or a tender document."""
from dataclasses import asdict
from functools import lru_cache

from . import audit
from .citations import find_citations
from .knowledge import KnowledgeBase, load_kb
from .pipeline import expand
from .pipeline.deliver import tender_clause
from .pipeline.ingest import ingest
from .pipeline.retrieve import Retriever
from .pipeline.understand import LANG_NAMES, detect_language, extract_attributes, split_items


class Engine:
    def __init__(self, kb: KnowledgeBase):
        self.kb = kb
        self.retriever = Retriever(kb)

    def _card(self, hit, text: str, lang: str) -> dict:
        s = self.kb.standards[hit.id]
        cited_year = next((c.year for c in find_citations(text) if (r := self.kb.resolve(c)) and r["id"] == hit.id), None)
        groups = expand.allied(self.kb, s["id"])
        return {
            "standard": expand.summary(self.kb, s) | {"scope": s["scope"], "domain": s["domain"],
                                                     "domain_name": self.kb.meta["domains"][s["domain"]]},
            "confidence": hit.confidence,
            "score": round(hit.score, 5),
            "evidence": {
                "matched_terms": hit.matched_terms,
                "cited_in_input": hit.cited,
                "dense_similarity": hit.dense_similarity,
                "scope_text": s["scope"],
            },
            "version": expand.version(self.kb, s, cited_year),
            "certification": expand.certification(self.kb, s),
            "allied": groups,
            "clause": tender_clause(self.kb, s, groups, lang),
        }

    def recommend(self, query: str, top_k: int = 5, output_language: str = "en") -> dict:
        lang = detect_language(query)
        attrs = extract_attributes(query)
        res = self.retriever.search(query, top_k)
        results = [self._card(h, query, output_language) for h in res.hits]
        request_id = audit.record("recommend", {
            "query": query[:500], "language": lang,
            "results": [r["standard"]["label"] for r in results], "abstained": res.abstained})
        return {
            "request_id": request_id,
            "query": query,
            "detected_language": {"code": lang, "name": LANG_NAMES.get(lang, lang)},
            "attributes": asdict(attrs),
            "expanded_terms": res.expanded_terms,
            "retrieval_mode": res.mode,
            "abstained": res.abstained,
            "abstain_reason": res.reason,
            "results": results,
            "data_as_of": self.kb.meta["as_of"],
        }

    def analyse_tender(self, name: str, data: bytes, output_language: str = "en") -> dict:
        doc = ingest(name, data)
        items = []
        for it in split_items(doc.text):
            res = self.retriever.search(it.text, top_k=3)
            primary = next((self.kb.standards[h.id] for h in res.hits
                            if self.kb.standards[h.id]["category"] == "product"), None)
            findings = expand.health_check(self.kb, it.text, primary)
            status = expand.item_status(findings, primary is not None)
            items.append({
                "index": it.index,
                "title": it.title,
                "text": it.text,
                "lines": [it.line_start, it.line_end],
                "language": detect_language(it.text),
                "attributes": asdict(extract_attributes(it.text)),
                "primary_standard": expand.summary(self.kb, primary) if primary else None,
                "confidence": res.hits[0].confidence if res.hits else 0.0,
                "abstained": res.abstained,
                "status": status,
                "status_label": expand.ITEM_STATUS[status],
                "findings": findings,
                "suggested_clause": tender_clause(self.kb, primary, expand.allied(self.kb, primary["id"]),
                                                  output_language) if primary else None,
            })
        counts = {"high": 0, "medium": 0, "low": 0, "info": 0}
        for it in items:
            for f in it["findings"]:
                counts[f["severity"]] += 1
        request_id = audit.record("tender_analyse", {"document": doc.name, "sha256": doc.sha256,
                                                     "items": len(items), "findings": counts})
        return {
            "request_id": request_id,
            "document": {"name": doc.name, "sha256": doc.sha256, "type": doc.kind, "pages": doc.pages,
                         "characters": len(doc.text), "ocr_pages": doc.ocr_pages, "warnings": doc.warnings},
            "summary": {"items": len(items), "findings": counts,
                        "status": (ts := expand.tender_status([i["status"] for i in items], readable=bool(doc.text.strip()))),
                        "status_label": expand.TENDER_STATUS[ts],
                        "items_by_status": {k: sum(1 for i in items if i["status"] == k) for k in expand.ITEM_STATUS},
                        "items_without_standard": sum(1 for i in items if i["abstained"])},
            "items": items,
            "data_as_of": self.kb.meta["as_of"],
        }


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    return Engine(load_kb())
