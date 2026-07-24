from __future__ import annotations

import hashlib
import json
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .config import LOG_DIR, SETTINGS


class AuditLog:
    def __init__(self, directory: Path = LOG_DIR) -> None:
        self.directory = directory
        self._lock = threading.Lock()
        self.directory.mkdir(parents=True, exist_ok=True)
        self._cleanup()

    def _cleanup(self) -> None:
        cutoff = datetime.now().date() - timedelta(days=SETTINGS.log_retention_days)
        for path in self.directory.glob("ui-actions-*.jsonl"):
            try:
                stamp = datetime.strptime(path.stem.removeprefix("ui-actions-"), "%Y-%m-%d").date()
                if stamp < cutoff:
                    path.unlink(missing_ok=True)
            except (ValueError, OSError):
                continue

    @staticmethod
    def redact_action(action: dict[str, Any]) -> dict[str, Any]:
        safe = dict(action)
        if "text" in safe:
            text = str(safe.pop("text"))
            safe["text_length"] = len(text)
            safe["text_sha256_prefix"] = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
        return safe

    def write(self, event: dict[str, Any]) -> None:
        now = datetime.now(timezone.utc).astimezone()
        record = {
            "timestamp": now.isoformat(timespec="milliseconds"),
            "request_source": event.pop("request_source", "remote"),
            **event,
        }
        path = self.directory / f"ui-actions-{now:%Y-%m-%d}.jsonl"
        with self._lock:
            with path.open("a", encoding="utf-8", newline="\n") as stream:
                stream.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")


AUDIT = AuditLog()
