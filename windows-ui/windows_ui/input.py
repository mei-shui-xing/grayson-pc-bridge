from __future__ import annotations

import ctypes
import time
from ctypes import wintypes
from typing import Any

import win32api
import win32con

from .audit import AUDIT, AuditLog
from .config import SETTINGS
from .control_state import CONTROL
from .native import get_cursor_position, user32
from .safety import (
    assess_foreground,
    assess_point,
    ensure_hotkey_allowed,
    ensure_text_target_safe,
)
from .windows import foreground_window


ULONG_PTR = wintypes.WPARAM


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD), ("wParamH", wintypes.WORD)]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("union",)
    _fields_ = [("type", wintypes.DWORD), ("union", _INPUTUNION)]


KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
INPUT_KEYBOARD = 1


VK: dict[str, int] = {
    "BACKSPACE": 0x08, "TAB": 0x09, "ENTER": 0x0D, "SHIFT": 0x10,
    "CTRL": 0x11, "ALT": 0x12, "PAUSE": 0x13, "CAPSLOCK": 0x14,
    "ESC": 0x1B, "SPACE": 0x20, "PAGEUP": 0x21, "PAGEDOWN": 0x22,
    "END": 0x23, "HOME": 0x24, "LEFT": 0x25, "UP": 0x26,
    "RIGHT": 0x27, "DOWN": 0x28, "INSERT": 0x2D, "DELETE": 0x2E,
    "WIN": 0x5B, "MENU": 0x5D,
}
VK.update({f"F{i}": 0x6F + i for i in range(1, 25)})
for code in range(ord("0"), ord("9") + 1):
    VK[chr(code)] = code
for code in range(ord("A"), ord("Z") + 1):
    VK[chr(code)] = code

ALIASES = {
    "CONTROL": "CTRL", "RETURN": "ENTER", "ESCAPE": "ESC",
    "WINDOWS": "WIN", "PGUP": "PAGEUP", "PGDN": "PAGEDOWN",
    "DEL": "DELETE", "INS": "INSERT",
}
EXTENDED = {VK[name] for name in ("LEFT", "UP", "RIGHT", "DOWN", "INSERT", "DELETE", "HOME", "END", "PAGEUP", "PAGEDOWN", "WIN")}

BUTTON_FLAGS = {
    "left": (win32con.MOUSEEVENTF_LEFTDOWN, win32con.MOUSEEVENTF_LEFTUP),
    "right": (win32con.MOUSEEVENTF_RIGHTDOWN, win32con.MOUSEEVENTF_RIGHTUP),
    "middle": (win32con.MOUSEEVENTF_MIDDLEDOWN, win32con.MOUSEEVENTF_MIDDLEUP),
}


def _key_name(value: str) -> str:
    name = value.strip().upper()
    return ALIASES.get(name, name)


def _vk(value: str) -> int:
    name = _key_name(value)
    if name in VK:
        return VK[name]
    if len(name) == 1:
        result = int(user32.VkKeyScanW(ord(name)))
        if result != -1:
            return result & 0xFF
    raise ValueError(f"Unsupported key: {value}")


def _send_vk(vk: int, key_up: bool = False) -> None:
    flags = (KEYEVENTF_KEYUP if key_up else 0) | (KEYEVENTF_EXTENDEDKEY if vk in EXTENDED else 0)
    event = INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(vk, 0, flags, 0, 0))
    if user32.SendInput(1, ctypes.byref(event), ctypes.sizeof(INPUT)) != 1:
        raise ctypes.WinError()


def type_unicode(text: str, interval_ms: int = 0) -> None:
    if len(text) > 10000:
        raise ValueError("type_text is limited to 10000 characters per action")
    encoded = text.encode("utf-16-le")
    for index in range(0, len(encoded), 2):
        unit = int.from_bytes(encoded[index:index + 2], "little")
        down = INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(0, unit, KEYEVENTF_UNICODE, 0, 0))
        up = INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(0, unit, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0, 0))
        events = (INPUT * 2)(down, up)
        if user32.SendInput(2, events, ctypes.sizeof(INPUT)) != 2:
            raise ctypes.WinError()
        if interval_ms:
            time.sleep(min(interval_ms, 1000) / 1000)


def press_key(key: str, presses: int = 1, interval_ms: int = 0) -> None:
    vk = _vk(key)
    for _ in range(max(1, min(int(presses), 100))):
        _send_vk(vk)
        _send_vk(vk, True)
        if interval_ms:
            time.sleep(min(interval_ms, 1000) / 1000)


def hotkey(keys: list[str]) -> None:
    if not keys or len(keys) > 6:
        raise ValueError("hotkey requires 1 to 6 keys")
    ensure_hotkey_allowed(keys)
    values = [_vk(key) for key in keys]
    for value in values:
        _send_vk(value)
    for value in reversed(values):
        _send_vk(value, True)


def _mouse_click(button: str, clicks: int = 1) -> None:
    if button not in BUTTON_FLAGS:
        raise ValueError("button must be left, right, or middle")
    down, up = BUTTON_FLAGS[button]
    for _ in range(clicks):
        win32api.mouse_event(down, 0, 0, 0, 0)
        win32api.mouse_event(up, 0, 0, 0, 0)
        if clicks > 1:
            time.sleep(0.08)


def _release_mouse() -> None:
    for _down, up in BUTTON_FLAGS.values():
        try:
            win32api.mouse_event(up, 0, 0, 0, 0)
        except Exception:
            pass


def _require_allowed_foreground(text_target: bool = False) -> dict[str, Any]:
    CONTROL.require_input()
    window, decision = assess_foreground()
    if not decision["allowed"]:
        raise PermissionError(decision["reason"])
    if text_target:
        ensure_text_target_safe()
    return window or {}


def _require_allowed_point(x: int, y: int) -> dict[str, Any]:
    CONTROL.require_input()
    window, decision = assess_point(x, y)
    if not decision["allowed"]:
        raise PermissionError(decision["reason"])
    return window or {}


def execute_action(action: dict[str, Any]) -> dict[str, Any]:
    action_type = str(action.get("type", "")).casefold()
    before = foreground_window()
    actual: dict[str, Any] = {}

    if action_type == "wait":
        milliseconds = max(0, min(int(action.get("milliseconds", 0)), SETTINGS.max_wait_milliseconds))
        time.sleep(milliseconds / 1000)
        actual["milliseconds"] = milliseconds
    elif action_type in {"move", "click", "double_click", "right_click", "mouse_down", "mouse_up"}:
        current_x, current_y = get_cursor_position()
        x = int(action.get("x", current_x))
        y = int(action.get("y", current_y))
        target = _require_allowed_point(x, y)
        user32.SetCursorPos(x, y)
        actual.update({"x": x, "y": y, "target_window": target})
        if action_type == "click":
            _mouse_click(str(action.get("button", "left")).casefold())
        elif action_type == "double_click":
            _mouse_click(str(action.get("button", "left")).casefold(), 2)
        elif action_type == "right_click":
            _mouse_click("right")
        elif action_type == "mouse_down":
            button = str(action.get("button", "left")).casefold()
            win32api.mouse_event(BUTTON_FLAGS[button][0], 0, 0, 0, 0)
        elif action_type == "mouse_up":
            button = str(action.get("button", "left")).casefold()
            win32api.mouse_event(BUTTON_FLAGS[button][1], 0, 0, 0, 0)
    elif action_type == "drag":
        start_x, start_y = get_cursor_position()
        from_x = int(action.get("from_x", start_x))
        from_y = int(action.get("from_y", start_y))
        to_x = int(action["x"])
        to_y = int(action["y"])
        _require_allowed_point(from_x, from_y)
        _require_allowed_point(to_x, to_y)
        button = str(action.get("button", "left")).casefold()
        duration = max(0.05, min(float(action.get("duration", 0.5)), 5.0))
        user32.SetCursorPos(from_x, from_y)
        win32api.mouse_event(BUTTON_FLAGS[button][0], 0, 0, 0, 0)
        steps = max(2, int(duration * 60))
        try:
            for step in range(1, steps + 1):
                fraction = step / steps
                user32.SetCursorPos(
                    round(from_x + (to_x - from_x) * fraction),
                    round(from_y + (to_y - from_y) * fraction),
                )
                time.sleep(duration / steps)
        finally:
            win32api.mouse_event(BUTTON_FLAGS[button][1], 0, 0, 0, 0)
        actual.update({"from_x": from_x, "from_y": from_y, "x": to_x, "y": to_y, "duration": duration})
    elif action_type == "scroll":
        current_x, current_y = get_cursor_position()
        x = int(action.get("x", current_x))
        y = int(action.get("y", current_y))
        _require_allowed_point(x, y)
        user32.SetCursorPos(x, y)
        amount = int(action.get("amount", action.get("clicks", -3)))
        horizontal = bool(action.get("horizontal", False))
        flag = win32con.MOUSEEVENTF_HWHEEL if horizontal else win32con.MOUSEEVENTF_WHEEL
        win32api.mouse_event(flag, 0, 0, amount * win32con.WHEEL_DELTA, 0)
        actual.update({"x": x, "y": y, "amount": amount, "horizontal": horizontal})
    elif action_type == "type_text":
        _require_allowed_foreground(text_target=True)
        text = str(action.get("text", ""))
        type_unicode(text, int(action.get("interval_ms", 0)))
        actual["characters"] = len(text)
    elif action_type == "press_key":
        _require_allowed_foreground()
        press_key(str(action["key"]), int(action.get("presses", 1)), int(action.get("interval_ms", 0)))
        actual["key"] = _key_name(str(action["key"]))
    elif action_type == "hotkey":
        _require_allowed_foreground()
        keys = [str(key) for key in action.get("keys", [])]
        hotkey(keys)
        actual["keys"] = [_key_name(key) for key in keys]
    else:
        raise ValueError(
            "Unsupported action type. Use move, click, double_click, right_click, mouse_down, mouse_up, "
            "drag, scroll, type_text, press_key, hotkey, or wait."
        )

    time.sleep(0.03)
    after = foreground_window()
    return {
        "success": True,
        "type": action_type,
        "actual": actual,
        "foreground_before": before,
        "foreground_after": after,
        "foreground_changed": (before or {}).get("hwnd") != (after or {}).get("hwnd"),
    }


def execute_actions(actions: list[dict[str, Any]]) -> dict[str, Any]:
    if not isinstance(actions, list) or not actions:
        raise ValueError("actions must be a non-empty list")
    if len(actions) > SETTINGS.max_batch_actions:
        raise ValueError(f"At most {SETTINGS.max_batch_actions} actions are allowed per batch")
    results: list[dict[str, Any]] = []
    aborted = False
    abort_reason: str | None = None

    for index, action in enumerate(actions):
        try:
            result = execute_action(action)
            result["index"] = index
            results.append(result)
            AUDIT.write({
                "action_type": result["type"],
                "action": AuditLog.redact_action(action),
                "target": result.get("actual"),
                "foreground_before": result.get("foreground_before"),
                "success": True,
                "refused_reason": None,
                "safety_intercept": False,
            })
            if index < len(actions) - 1:
                window, decision = assess_foreground()
                if not decision["allowed"]:
                    aborted = True
                    abort_reason = f"Foreground left the allowlist after action {index}: {decision['reason']}"
                    break
        except Exception as error:
            aborted = True
            abort_reason = str(error)
            result = {
                "index": index,
                "success": False,
                "type": str(action.get("type", "")),
                "error": abort_reason,
                "foreground_before": foreground_window(),
            }
            results.append(result)
            AUDIT.write({
                "action_type": result["type"],
                "action": AuditLog.redact_action(action),
                "foreground_before": result.get("foreground_before"),
                "success": False,
                "refused_reason": abort_reason,
                "safety_intercept": isinstance(error, PermissionError),
            })
            _release_mouse()
            break

    return {
        "success": not aborted,
        "aborted": aborted,
        "abort_reason": abort_reason,
        "completed_actions": sum(1 for item in results if item.get("success")),
        "requested_actions": len(actions),
        "results": results,
        "foreground": foreground_window(),
    }
