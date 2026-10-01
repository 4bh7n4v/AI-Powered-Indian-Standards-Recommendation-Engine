"""Summarise the server logs: traffic per endpoint, status codes, latency, uploads and errors.

    python -m app.log_report                 # all log files in ISRE_LOG_DIR
    python -m app.log_report --since 2026-10-01
    python -m app.log_report --json          # machine-readable output
"""
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from .config import LOG_DIR


def load(since: str | None) -> list[dict]:
    rows = []
    for path in sorted(LOG_DIR.glob("server.jsonl*")):
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not since or row.get("time", "") >= since:
                rows.append(row)
    return sorted(rows, key=lambda r: r.get("time", ""))


def pct(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    return values[min(len(values) - 1, round(p / 100 * (len(values) - 1)))]


def summarise(rows: list[dict]) -> dict:
    requests = [r for r in rows if r.get("event") == "request" and r.get("path", "").startswith("/api/")]
    uploads = [r for r in rows if r.get("event") == "upload"]
    by_path: dict[str, list[dict]] = defaultdict(list)
    for r in requests:
        by_path[f'{r["method"]} {r["path"]}'].append(r)
    return {
        "period": {"from": rows[0]["time"] if rows else None, "to": rows[-1]["time"] if rows else None},
        "log_lines": len(rows),
        "api_requests": len(requests),
        "status_codes": dict(sorted(Counter(r["status"] for r in requests).items())),
        "endpoints": {
            k: {"count": len(v), "errors": sum(1 for r in v if r["status"] >= 400),
                "p50_ms": pct([r["duration_ms"] for r in v], 50), "p95_ms": pct([r["duration_ms"] for r in v], 95),
                "max_ms": max(r["duration_ms"] for r in v)}
            for k, v in sorted(by_path.items(), key=lambda kv: -len(kv[1]))
        },
        "uploads": {"count": len(uploads),
                    "tender_status": dict(Counter(u["status"] for u in uploads if "status" in u)),
                    "file_types": dict(Counter(Path(u.get("filename") or "").suffix.lower() or "(none)" for u in uploads)),
                    "rejected": sum(1 for u in uploads if u["level"] == "WARNING")},
        "errors": [{"time": r["time"], "level": r["level"], "logger": r["logger"], "message": r["message"],
                    "request_id": r.get("request_id")}
                   for r in rows if r["level"] in ("ERROR", "CRITICAL")][-20:],
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--since", help="ISO date or timestamp, e.g. 2026-10-01")
    ap.add_argument("--json", action="store_true", help="print JSON instead of a text report")
    args = ap.parse_args()
    report = summarise(load(args.since))
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return
    print(f"Log directory : {LOG_DIR}")
    print(f"Period        : {report['period']['from']} -> {report['period']['to']}")
    print(f"API requests  : {report['api_requests']}   status codes: {report['status_codes']}")
    print("\nEndpoint                                   count  errors   p50 ms   p95 ms   max ms")
    for k, v in report["endpoints"].items():
        print(f"{k:<42}{v['count']:>6}{v['errors']:>8}{v['p50_ms']:>9.1f}{v['p95_ms']:>9.1f}{v['max_ms']:>9.1f}")
    u = report["uploads"]
    print(f"\nUploads       : {u['count']} (rejected {u['rejected']})  types: {u['file_types']}")
    print(f"Tender result : {u['tender_status']}")
    print(f"\nRecent errors : {len(report['errors'])}")
    for e in report["errors"]:
        print(f"  {e['time']} [{e['request_id']}] {e['logger']}: {e['message']}")


if __name__ == "__main__":
    main()
