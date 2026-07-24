from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .audit import AUDIT
from .config import RUNTIME_DIR, SETTINGS


class ControlState:
    VALID = {"active", "paused", "emergency"}

    def __init__(self, path: Path = RUNTIME_DIR / "ui-status.json") -> None:
        self.path = path
        self._lock = threading.RLock()
        self._callbacks: list[Callable[[dict[str, Any]], None]] = []
        self._state = "active"
        self._reason = "startup"
        self._hotkey = SETTINGS.emergency_hotkey
        self._last_error: str | None = None
        self._load_or_initialize()

    def _load_or_initialize(self) -> None:
        # A previous emergency stop remains sticky across restarts. Paused is also
        # preserved; a clean active shutdown starts active next time.
        try:
            previous = json.loads(self.path.read_text(encoding="utf-8"))
            if previous.get("state") in {"paused", "emergency"}:
                self._state = previous["state"]
                self._reason = previous.get("reason", "preserved from previous run")
        except (OSError, ValueError, TypeError):
            pass
        self._write()

    def _snapshot(self) -> dict[str, Any]:
        return {
            "uiPid": os.getpid(),
            "state": self._state,
            "canRead": True,
            "canInput": self._state == "active",
            "reason": self._reason,
            "emergencyHotkey": self._hotkey,
            "lastError": self._last_error,
            "updatedAt": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        }

    def _write(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = self._snapshot()
        temp = self.path.with_suffix(f".{os.getpid()}.tmp")
        temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        try:
            self.path.unlink(missing_ok=True)
            temp.replace(self.path)
        finally:
            temp.unlink(missing_ok=True)
        for callback in list(self._callbacks):
            try:
                callback(dict(payload))
            except Exception:
                continue

    def subscribe(self, callback: Callable[[dict[str, Any]], None]) -> None:
        with self._lock:
            self._callbacks.append(callback)

    def status(self) -> dict[str, Any]:
        with self._lock:
            return self._snapshot()

    def set_hotkey(self, value: str) -> None:
        with self._lock:
            self._hotkey = value
            self._write()

    def set_error(self, value: str | None) -> None:
        with self._lock:
            self._last_error = value
            self._write()

    def pause(self, reason: str = "remote pause request") -> dict[str, Any]:
        with self._lock:
            if self._state != "emergency":
                self._state = "paused"
                self._reason = reason
                self._write()
                AUDIT.write({"action_type": "control_pause", "success": True, "safety_intercept": False})
            return self._snapshot()

    def resume(self, *, local: bool = False) -> dict[str, Any]:
        with self._lock:
            if self._state == "emergency" and not local:
                raise PermissionError("Emergency stop is active. Recovery must be confirmed locally from the tray menu or local resume command.")
            self._state = "active"
            self._reason = "local recovery" if local else "remote resume request"
            self._write()
            AUDIT.write({"action_type": "control_resume", "success": True, "local": local, "safety_intercept": False})
            return self._snapshot()

    def emergency_stop(self, reason: str = "local emergency hotkey") -> dict[str, Any]:
        with self._lock:
            self._state = "emergency"
            self._reason = reason
            self._write()
            AUDIT.write({"action_type": "emergency_stop", "success": True, "local": True, "safety_intercept": True})
            return self._snapshot()

    def require_input(self) -> None:
        with self._lock:
            if self._state != "active":
                raise PermissionError(f"Remote input is disabled: state={self._state}, reason={self._reason}")


CONTROL = ControlState()
