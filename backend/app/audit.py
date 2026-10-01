"""Append-only audit log. Each entry carries the hash of the previous one (tamper evident)."""
import hashlib
import json
import threading
import uuid
from datetime import datetime, timezone

from .config import VAR_DIR

_lock = threading.Lock()
LOG_PATH = VAR_DIR / "audit.jsonl"


def _last_hash() -> str:
    if not LOG_PATH.exists():
        return "0" * 64
    last = None
    with LOG_PATH.open("rb") as f:
        for line in f:
            if line.strip():
                last = line
    return json.loads(last)["hash"] if last else "0" * 64


def record(event: str, payload: dict) -> str:
    entry_id = uuid.uuid4().hex[:12]
    with _lock:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        entry = {"id": entry_id, "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                 "event": event, "payload": payload, "prev": _last_hash()}
        entry["hash"] = hashlib.sha256(json.dumps(entry, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry_id


def verify() -> bool:
    prev = "0" * 64
    if not LOG_PATH.exists():
        return True
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        e = json.loads(line)
        h = e.pop("hash")
        if e["prev"] != prev or hashlib.sha256(json.dumps(e, sort_keys=True, ensure_ascii=False).encode()).hexdigest() != h:
            return False
        prev = h
    return True
