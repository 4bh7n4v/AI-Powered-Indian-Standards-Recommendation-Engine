"""Server logging: human-readable lines on the console, JSON lines on disk for later analysis.

Every record goes to LOG_DIR/server.jsonl, rotated at midnight UTC and kept for LOG_RETENTION_DAYS.
Pass structured fields with `log.info("...", extra={"ctx": {...}})`; they become top-level JSON keys.
"""
import json
import logging
import sys
from datetime import datetime, timezone
from logging.handlers import TimedRotatingFileHandler

from .config import LOG_DIR, LOG_LEVEL, LOG_RETENTION_DAYS

LOG_FILE = LOG_DIR / "server.jsonl"
_MARK = "_isre_handler"


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {"time": datetime.fromtimestamp(record.created, timezone.utc).isoformat(timespec="milliseconds"),
                 "level": record.levelname, "logger": record.name, "message": record.getMessage()}
        entry |= getattr(record, "ctx", None) or {}
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False, default=str)


def setup() -> None:
    """Attach the console and file handlers once. Safe to call repeatedly."""
    root = logging.getLogger()
    if any(getattr(h, _MARK, False) for h in root.handlers):
        return
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    file_handler = TimedRotatingFileHandler(LOG_FILE, when="midnight", utc=True,
                                            backupCount=LOG_RETENTION_DAYS, encoding="utf-8")
    file_handler.setFormatter(JsonFormatter())
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s"))
    for h in (file_handler, console):
        setattr(h, _MARK, True)
        root.addHandler(h)
    root.setLevel(LOG_LEVEL)
    # Uvicorn's own loggers do not propagate to root; route them through the same handlers.
    for name in ("uvicorn", "uvicorn.error"):
        lg = logging.getLogger(name)
        lg.handlers, lg.propagate = [], True
    # Requests are logged by the middleware in main.py, so uvicorn's access log is redundant.
    logging.getLogger("uvicorn.access").disabled = True
