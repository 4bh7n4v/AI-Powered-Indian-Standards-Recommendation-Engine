"""Stage 4 - Expand & Annotate: allied standards, versions, certification, tender health check."""
import re

from ..citations import find_citations
from ..knowledge import KnowledgeBase

ALLIED_ORDER = ["normative_ref", "test_method", "terminology", "safety", "installation", "related_product"]
CERT_MENTION_RE = re.compile(r"\b(ISI|BIS|standard mark|licen[cs]e|CRS|registration|hallmark\w*|HUID)\b", re.I)


def summary(kb: KnowledgeBase, s: dict) -> dict:
    return {"id": s["id"], "label": kb.label(s), "number": s["number"], "year": s.get("year"),
            "title": s["title"], "category": s["category"]}


def allied(kb: KnowledgeBase, sid: str) -> dict:
    """One hop over typed edges, grouped by the six allied types named in the PS."""
    groups: dict[str, list[dict]] = {t: [] for t in ALLIED_ORDER}
    referenced_by = []
    for a, b, t in kb.edges:
        if a == sid:
            groups[t].append(summary(kb, kb.standards[b]))
        elif b == sid and t != "related_product":
            referenced_by.append(summary(kb, kb.standards[a]))
    out = {t: v for t, v in groups.items() if v}
    if referenced_by:
        out["referenced_by"] = referenced_by
    return out


def version(kb: KnowledgeBase, s: dict, cited_year: int | None = None) -> dict:
    current = s.get("year")
    outdated = bool(cited_year and current and cited_year < current)
    return {
        "current_edition": kb.label(s),
        "year": current,
        "status": "current",
        "amendments": s.get("amendments", []),
        "amendments_note": None if s.get("amendments") else "Amendment list not yet loaded; check the BIS portal.",
        "superseded_editions": s.get("superseded_editions", []),
        "cited_year": cited_year,
        "cited_is_outdated": outdated,
        "as_of": kb.meta["as_of"],
        "verified": kb.meta.get("verified", False),
    }


def certification(kb: KnowledgeBase, s: dict) -> list[dict]:
    """Certification *suggestion* with its basis. Never a legal verdict."""
    if s["category"] != "product":
        return []
    out = []
    for rule in kb.cert["rules"]:
        if s["id"] in rule["applies_to"]:
            scheme = kb.cert["schemes"][rule["scheme"]]
            out.append({
                "scheme": rule["scheme"],
                "label": scheme["short"],
                "name": scheme["name"],
                "basis": rule["order"],
                "effective_from": rule.get("effective_from"),
                "status": "likely_mandatory" if not rule.get("verified") else "mandatory",
                "verified": bool(rule.get("verified")),
                "rule_id": rule["id"],
            })
    if not out:
        out.append({"scheme": None, "label": "No mandatory scheme found", "name": None,
                    "basis": f"Not listed in rule pack version {kb.cert['version']}",
                    "effective_from": None, "status": "none_found", "verified": False, "rule_id": None})
    return out


def health_check(kb: KnowledgeBase, item_text: str, primary: dict | None) -> list[dict]:
    """Findings for one tender item: missing, outdated or incomplete standards."""
    findings = []
    cited_ids = set()
    for c in find_citations(item_text):
        rec = kb.resolve(c)
        if not rec:
            findings.append({"severity": "info", "kind": "not_in_registry", "citation": c.raw,
                             "message": f"{c.raw} is not in the verified registry; check it manually."})
            continue
        cited_ids.add(rec["id"])
        v = version(kb, rec, c.year)
        if v["cited_is_outdated"]:
            findings.append({"severity": "high", "kind": "outdated", "citation": c.raw, "standard_id": rec["id"],
                             "message": f"{c.raw} cites an old edition. Current edition is {kb.label(rec)}.",
                             "fix": f"Replace with {kb.label(rec)} (latest edition, with all amendments)."})
        elif c.year is None and rec.get("year"):  # 'all parts' series have no single edition
            findings.append({"severity": "low", "kind": "no_edition", "citation": c.raw, "standard_id": rec["id"],
                             "message": f"{c.raw} does not state an edition.",
                             "fix": f"Cite {kb.label(rec)} and add 'with all amendments'."})
    if primary and primary["id"] not in cited_ids:
        findings.append({"severity": "high", "kind": "missing", "standard_id": primary["id"],
                         "message": f"The item appears to fall under {kb.label(primary)} ({primary['title']}), "
                                    "which is not cited.",
                         "fix": f"Add: shall conform to {kb.label(primary)}."})
    if primary:
        groups = allied(kb, primary["id"])
        for kind in ("test_method", "safety"):
            missing = [a for a in groups.get(kind, []) if a["id"] not in cited_ids]
            if missing:
                labels = ", ".join(a["label"] for a in missing)
                findings.append({"severity": "medium", "kind": f"incomplete_{kind}", "standard_ids": [a["id"] for a in missing],
                                 "message": f"No {kind.replace('_', ' ')} standard cited for {kb.label(primary)}.",
                                 "fix": f"Consider adding: {labels}."})
        certs = [c for c in certification(kb, primary) if c["scheme"]]
        if certs and not CERT_MENTION_RE.search(item_text):
            findings.append({"severity": "medium", "kind": "certification_not_stated", "standard_id": primary["id"],
                             "message": f"{certs[0]['label']} appears to apply ({certs[0]['basis']}) but the "
                                        "item does not ask for it.",
                             "fix": "Add the certification clause (see suggested clause)."})
    order = {"high": 0, "medium": 1, "low": 2, "info": 3}
    return sorted(findings, key=lambda f: order[f["severity"]])


ITEM_STATUS = {
    "acceptable": "Acceptable",
    "needs_revision": "Needs revision",
    "not_acceptable": "Not acceptable",
    "not_applicable": "No applicable IS",
}
TENDER_STATUS = {
    "acceptable": "Acceptable",
    "partially_acceptable": "Partially acceptable",
    "not_acceptable": "Not acceptable",
    "not_applicable": "No Indian Standard applies",
    "unreadable": "Could not read document",
}


def item_status(findings: list[dict], has_standard: bool) -> str:
    """high finding -> not acceptable; medium -> needs revision; low/info only -> acceptable."""
    if not has_standard and not findings:
        return "not_applicable"
    severities = {f["severity"] for f in findings}
    if "high" in severities:
        return "not_acceptable"
    if "medium" in severities:
        return "needs_revision"
    return "acceptable"


def tender_status(statuses: list[str], readable: bool = True) -> str:
    """Overall readiness of the tender, ignoring items where no IS applies (e.g. services)."""
    if not statuses and not readable:
        return "unreadable"
    relevant = [s for s in statuses if s != "not_applicable"]
    if not relevant:
        return "not_applicable"
    if all(s == "acceptable" for s in relevant):
        return "acceptable"
    if not any(s == "acceptable" for s in relevant) and any(s == "not_acceptable" for s in relevant):
        return "not_acceptable"
    return "partially_acceptable"
