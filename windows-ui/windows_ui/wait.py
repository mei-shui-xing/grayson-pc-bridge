from __future__ import annotations

import math
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import psutil
from PIL import ImageChops, ImageStat

from .screenshot import CaptureResult, capture
from .uia import control_exists, text_exists
from .windows import foreground_window, list_windows


@dataclass(slots=True)
class WaitResult:
    payload: dict[str, Any]
    screenshot: CaptureResult | None = None


def _process_matches(name: str | None = None, pid: int | None = None) -> bool:
    for process in psutil.process_iter(["pid", "name"]):
        try:
            if pid is not None and process.info["pid"] == int(pid):
                return True
            if name and re.search(name, process.info.get("name") or "", re.IGNORECASE):
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False


def _region_difference(first: CaptureResult, second: CaptureResult) -> float:
    a = first.image.convert("RGB")
    b = second.image.convert("RGB")
    if a.size != b.size:
        return 1.0
    stat = ImageStat.Stat(ImageChops.difference(a, b))
    rms = math.sqrt(sum(value * value for value in stat.rms) / max(1, len(stat.rms)))
    return round(rms / 255.0, 6)


def wait_for(
    condition: dict[str, Any],
    timeout_ms: int = 15000,
    interval_ms: int = 250,
    screenshot_on_timeout: bool = True,
) -> WaitResult:
    kind = str(condition.get("type", "")).casefold()
    timeout_ms = max(100, min(int(timeout_ms), 300000))
    interval_ms = max(50, min(int(interval_ms), 5000))
    started = time.monotonic()
    initial_foreground = foreground_window()
    baseline: CaptureResult | None = None
    last_difference: float | None = None
    if kind == "region_changed":
        baseline = capture(target="region", region=condition.get("region"), image_format="jpeg", quality=60)

    def check() -> tuple[bool, dict[str, Any]]:
        nonlocal last_difference
        if kind in {"window_appears", "window_disappears"}:
            selector = condition.get("window", {})
            matches = list_windows(
                title=selector.get("title"),
                process=selector.get("process"),
                pid=selector.get("pid"),
                include_hidden=bool(selector.get("include_hidden", False)),
            )
            matched = bool(matches)
            return (matched if kind == "window_appears" else not matched), {"matches": matches[:20]}
        if kind in {"process_starts", "process_ends"}:
            matched = _process_matches(condition.get("process"), condition.get("pid"))
            return (matched if kind == "process_starts" else not matched), {"process_found": matched}
        if kind == "foreground_changes":
            current = foreground_window()
            changed = (initial_foreground or {}).get("hwnd") != (current or {}).get("hwnd")
            return changed, {"initial_foreground": initial_foreground, "current_foreground": current}
        if kind == "control_appears":
            matched = control_exists(
                name=condition.get("name"),
                control_type=condition.get("control_type"),
                window=condition.get("window"),
            )
            return matched, {"control_found": matched}
        if kind == "text_appears":
            if not condition.get("text"):
                raise ValueError("text is required for text_appears")
            matched = text_exists(str(condition["text"]), window=condition.get("window"))
            return matched, {"text_found": matched}
        if kind == "region_changed":
            current = capture(target="region", region=condition.get("region"), image_format="jpeg", quality=60)
            last_difference = _region_difference(baseline, current)  # type: ignore[arg-type]
            threshold = float(condition.get("threshold", 0.05))
            return last_difference >= threshold, {"difference": last_difference, "threshold": threshold}
        raise ValueError(
            "condition.type must be window_appears, window_disappears, control_appears, text_appears, "
            "process_starts, process_ends, region_changed, or foreground_changes"
        )

    detail: dict[str, Any] = {}
    while True:
        try:
            matched, detail = check()
        except Exception as error:
            detail = {"last_check_error": str(error)}
            matched = False
        elapsed_ms = round((time.monotonic() - started) * 1000)
        if matched:
            return WaitResult({
                "matched": True,
                "timed_out": False,
                "condition": condition,
                "elapsed_ms": elapsed_ms,
                "detail": detail,
                "completed_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="milliseconds"),
            })
        if elapsed_ms >= timeout_ms:
            shot = capture(target="full", image_format="jpeg", quality=70) if screenshot_on_timeout else None
            return WaitResult({
                "matched": False,
                "timed_out": True,
                "condition": condition,
                "elapsed_ms": elapsed_ms,
                "detail": detail,
                "completed_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="milliseconds"),
            }, shot)
        time.sleep(interval_ms / 1000)
