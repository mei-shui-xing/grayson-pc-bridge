from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def _root() -> Path:
    return Path(os.environ.get("WINDOWS_UI_ROOT", Path(__file__).resolve().parents[1]))


ROOT = _root()
CONFIG_PATH = Path(os.environ.get("WINDOWS_UI_CONFIG", ROOT / "config" / "allowlist.json"))
RUNTIME_DIR = Path(os.environ.get("WINDOWS_UI_RUNTIME_DIR", ROOT / "runtime"))
LOG_DIR = Path(os.environ.get("WINDOWS_UI_LOG_DIR", ROOT / "logs"))


@dataclass(slots=True)
class Settings:
    allowed_processes: set[str] = field(default_factory=set)
    conditional_processes: set[str] = field(default_factory=set)
    allowed_window_title_patterns: list[str] = field(default_factory=list)
    forbidden_processes: set[str] = field(default_factory=set)
    forbidden_window_title_patterns: list[str] = field(default_factory=list)
    blocked_hotkeys: set[str] = field(default_factory=set)
    emergency_hotkey: str = "CTRL+ALT+PAUSE"
    emergency_hotkey_fallback: str = "CTRL+ALT+F12"
    log_retention_days: int = 14
    max_batch_actions: int = 100
    max_wait_milliseconds: int = 30000
    max_snapshot_nodes: int = 250
    max_snapshot_depth: int = 8

    @classmethod
    def load(cls, path: Path = CONFIG_PATH) -> "Settings":
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            allowed_processes={x.casefold() for x in data.get("allowed_processes", [])},
            conditional_processes={x.casefold() for x in data.get("conditional_processes", [])},
            allowed_window_title_patterns=list(data.get("allowed_window_title_patterns", [])),
            forbidden_processes={x.casefold() for x in data.get("forbidden_processes", [])},
            forbidden_window_title_patterns=list(data.get("forbidden_window_title_patterns", [])),
            blocked_hotkeys={_normalize_hotkey(x) for x in data.get("blocked_hotkeys", [])},
            emergency_hotkey=data.get("emergency_hotkey", "CTRL+ALT+PAUSE"),
            emergency_hotkey_fallback=data.get("emergency_hotkey_fallback", "CTRL+ALT+F12"),
            log_retention_days=int(data.get("log_retention_days", 14)),
            max_batch_actions=int(data.get("max_batch_actions", 100)),
            max_wait_milliseconds=int(data.get("max_wait_milliseconds", 30000)),
            max_snapshot_nodes=int(data.get("max_snapshot_nodes", 250)),
            max_snapshot_depth=int(data.get("max_snapshot_depth", 8)),
        )


def _normalize_hotkey(value: str | list[str]) -> str:
    parts = value if isinstance(value, list) else value.replace(" ", "").split("+")
    aliases = {"CONTROL": "CTRL", "WINDOWS": "WIN", "ESCAPE": "ESC", "RETURN": "ENTER"}
    return "+".join(aliases.get(str(part).upper(), str(part).upper()) for part in parts)


SETTINGS = Settings.load()
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)
