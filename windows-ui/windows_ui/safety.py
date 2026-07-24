from __future__ import annotations

import re
from typing import Any

from .config import SETTINGS, _normalize_hotkey
from .native import root_window_from_point
from .windows import foreground_window, window_info


def _matches(patterns: list[str], value: str) -> bool:
    return any(re.search(pattern, value, flags=re.IGNORECASE) for pattern in patterns)


def assess_window(window: dict[str, Any] | None) -> dict[str, Any]:
    if not window:
        return {"allowed": False, "reason": "No foreground or target window", "safety_intercept": True}
    process = str(window.get("process", "")).casefold()
    title = str(window.get("title", ""))
    if process in SETTINGS.forbidden_processes:
        return {"allowed": False, "reason": f"Forbidden process: {window.get('process')}", "safety_intercept": True}
    if _matches(SETTINGS.forbidden_window_title_patterns, title):
        return {"allowed": False, "reason": f"Forbidden window title: {title}", "safety_intercept": True}
    if process in SETTINGS.conditional_processes:
        if _matches(SETTINGS.allowed_window_title_patterns, title):
            return {"allowed": True, "reason": "Allowed project terminal", "safety_intercept": False}
        return {"allowed": False, "reason": "Terminal is not identified as belonging to this project", "safety_intercept": True}
    if process in SETTINGS.allowed_processes:
        return {"allowed": True, "reason": "Allowed process", "safety_intercept": False}
    if _matches(SETTINGS.allowed_window_title_patterns, title):
        return {"allowed": True, "reason": "Allowed window title", "safety_intercept": False}
    return {"allowed": False, "reason": f"Window is not on the allowlist: {window.get('process')} / {title}", "safety_intercept": True}


def assess_foreground() -> tuple[dict[str, Any] | None, dict[str, Any]]:
    window = foreground_window()
    return window, assess_window(window)


def assess_point(x: int, y: int) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    hwnd = root_window_from_point(x, y)
    try:
        window = window_info(hwnd) if hwnd else None
    except Exception:
        window = None
    return window, assess_window(window)


def ensure_hotkey_allowed(keys: list[str]) -> None:
    normalized = _normalize_hotkey(keys)
    if normalized in SETTINGS.blocked_hotkeys:
        raise PermissionError(f"High-risk hotkey is blocked: {normalized}")


def focused_control_is_password() -> bool:
    try:
        from pywinauto.uia_defines import IUIA
        from pywinauto.uia_element_info import UIAElementInfo

        element = IUIA().iuia.GetFocusedElement()
        info = UIAElementInfo(element)
        return bool(getattr(info, "is_password", False))
    except Exception:
        # Failure to inspect should not make ordinary custom-canvas apps unusable.
        # Title/process denylists still apply; explicit password controls fail closed
        # when UIA exposes them.
        return False


def ensure_text_target_safe() -> None:
    if focused_control_is_password():
        raise PermissionError("Typing into a password control is blocked")
