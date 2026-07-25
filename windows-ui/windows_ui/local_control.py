from __future__ import annotations

import json
import os
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import RUNTIME_DIR
COMMAND_PATH = RUNTIME_DIR / "local-command.json"
RESPONSE_PATH = RUNTIME_DIR / "local-command-response.json"


class LocalCommandWatcher:
    def __init__(self) -> None:
        self._stop = threading.Event()
        self._last_id: str | None = None
        self._thread = threading.Thread(target=self._run, name="windows-ui-local-control", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        # Import the process-owning state only inside the server watcher.  The
        # standalone CLI also imports this module; importing CONTROL there
        # would overwrite ui-status.json with the short-lived CLI process ID.
        from .control_state import CONTROL

        while not self._stop.wait(0.2):
            try:
                command = json.loads(COMMAND_PATH.read_text(encoding="utf-8"))
                command_id = str(command.get("id", ""))
                if not command_id or command_id == self._last_id:
                    continue
                self._last_id = command_id
                action = str(command.get("action", "")).casefold()
                if action == "pause":
                    result = CONTROL.pause("local stop script")
                elif action == "resume":
                    result = CONTROL.resume(local=True)
                elif action == "emergency":
                    result = CONTROL.emergency_stop("local command")
                else:
                    raise ValueError(f"Unknown local action: {action}")
                response = {"id": command_id, "success": True, "result": result}
            except (OSError, json.JSONDecodeError):
                continue
            except Exception as error:
                response = {"id": self._last_id, "success": False, "error": str(error)}
            try:
                RESPONSE_PATH.write_text(json.dumps(response, ensure_ascii=False, indent=2), encoding="utf-8")
            except OSError:
                continue


def send_local_command(action: str, timeout: float = 3.0) -> dict[str, Any]:
    command_id = uuid.uuid4().hex
    payload = {
        "id": command_id,
        "action": action,
        "requester_pid": os.getpid(),
        "requested_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    }
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    COMMAND_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            response = json.loads(RESPONSE_PATH.read_text(encoding="utf-8"))
            if response.get("id") == command_id:
                return response
        except (OSError, json.JSONDecodeError):
            pass
        time.sleep(0.1)
    return {"id": command_id, "success": False, "error": "Windows UI module did not answer the local command"}
