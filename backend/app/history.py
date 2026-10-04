"""Past checks and dashboard numbers, read from the audit log (no extra database).

Each tender analysis and standards search is already an audit entry. The full response is also
saved under var/results/<id>.json so a past check can be reopened exactly as it was shown.
"""
import json
import re
from collections import Counter

from . import audit
from .config import VAR_DIR

RESULTS = VAR_DIR / "results"
ID_RE = re.compile(r"^[0-9a-f]{12}$")
KINDS = {"tender_analyse": "tender", "recommend": "search"}


def save(result: dict) -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / f"{result['request_id']}.json").write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")


def load(entry_id: str) -> dict | None:
    if not ID_RE.match(entry_id):
        return None
    path = RESULTS / f"{entry_id}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def _entries() -> list[dict]:
    if not audit.LOG_PATH.exists():
        return []
    out = []
    for line in audit.LOG_PATH.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _row(e: dict) -> dict:
    p, kind = e["payload"], KINDS[e["event"]]
    if kind == "tender":
        f = p.get("findings", {})
        return {"id": e["id"], "time": e["time"], "kind": kind, "title": p.get("document", "document"),
                "source": p.get("source", "upload"), "status": p.get("status"), "status_label": p.get("status_label"),
                "items": p.get("items", 0), "issues": f.get("high", 0) + f.get("medium", 0),
                "standards": p.get("standards", []), "reopen": (RESULTS / f"{e['id']}.json").exists()}
    abstained = p.get("abstained", False)
    return {"id": e["id"], "time": e["time"], "kind": kind, "title": p.get("query", ""), "source": "search",
            "status": "not_applicable" if abstained else "matched",
            "status_label": "No applicable IS" if abstained else "Standards found",
            "items": None, "issues": None, "standards": p.get("results", [])[:3],
            "reopen": (RESULTS / f"{e['id']}.json").exists()}


def list_checks(limit: int = 50, kind: str | None = None) -> list[dict]:
    rows = [_row(e) for e in _entries() if e["event"] in KINDS]
    if kind:
        rows = [r for r in rows if r["kind"] == kind]
    return rows[::-1][:limit]


def stats() -> dict:
    entries = _entries()
    tenders = [e["payload"] for e in entries if e["event"] == "tender_analyse"]
    searches = [e["payload"] for e in entries if e["event"] == "recommend"]
    feedback = Counter(e["payload"].get("decision") for e in entries if e["event"] == "feedback")
    by_status = Counter(t["status"] for t in tenders if t.get("status"))
    items = Counter()
    findings = Counter()
    gaps, matched = Counter(), Counter()
    for t in tenders:
        items.update(t.get("items_by_status", {}))
        findings.update(t.get("findings", {}))
        gaps.update(t.get("gaps", []))
        matched.update(t.get("standards", []))
    for s in searches:
        matched.update(s.get("results", [])[:1])
    checked = [e for e in entries if e["event"] in KINDS]
    return {
        "checks": {"total": len(checked), "tenders": len(tenders), "searches": len(searches)},
        "items": {"total": sum(t.get("items", 0) for t in tenders),
                  "by_status": {k: items.get(k, 0) for k in ("acceptable", "needs_revision", "not_acceptable", "not_applicable")}},
        "tenders_by_status": {k: by_status.get(k, 0) for k in
                              ("acceptable", "partially_acceptable", "not_acceptable", "not_applicable", "unreadable")},
        "findings": {k: findings.get(k, 0) for k in ("high", "medium", "low", "info")},
        "searches_without_match": sum(1 for s in searches if s.get("abstained")),
        "feedback": {"accept": feedback.get("accept", 0), "reject": feedback.get("reject", 0)},
        "top_gaps": [{"label": k, "count": v} for k, v in gaps.most_common(5)],
        "top_standards": [{"label": k, "count": v} for k, v in matched.most_common(5)],
        "first_check": checked[0]["time"] if checked else None,
        "last_check": checked[-1]["time"] if checked else None,
        "recent": list_checks(6),
    }
