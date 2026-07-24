from __future__ import annotations

import ctypes
import re
import time
from dataclasses import dataclass
from typing import Any

import psutil
import win32api
import win32con
import win32gui
import win32process

from .native import get_window_dpi, rect_dict, user32


@dataclass(slots=True)
class WindowSelector:
    hwnd: int | None = None
    title: str | None = None
    process: str | None = None
    pid: int | None = None


def _process_name(pid: int) -> str:
    try:
        return psutil.Process(pid).name()
    except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
        return ""


def monitors() -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    for index, (handle, _hdc, rect) in enumerate(win32api.EnumDisplayMonitors(None, None)):
        info = win32api.GetMonitorInfo(handle)
        values.append({
            "index": index,
            "device": info.get("Device", ""),
            "primary": bool(info.get("Flags", 0) & 1),
            "bounds": rect_dict(tuple(rect)),
            "work_area": rect_dict(tuple(info.get("Work", rect))),
            "handle": int(handle),
        })
    return values


def monitor_for_rect(rect: tuple[int, int, int, int]) -> dict[str, Any] | None:
    handle = win32api.MonitorFromRect(rect, win32con.MONITOR_DEFAULTTONEAREST)
    for item in monitors():
        if item["handle"] == int(handle):
            return {key: value for key, value in item.items() if key != "handle"}
    return None


def window_info(hwnd: int) -> dict[str, Any]:
    if not hwnd or not win32gui.IsWindow(hwnd):
        raise ValueError(f"Window handle is not valid: {hwnd}")
    title = win32gui.GetWindowText(hwnd)
    _thread, pid = win32process.GetWindowThreadProcessId(hwnd)
    rect = tuple(win32gui.GetWindowRect(hwnd))
    placement = win32gui.GetWindowPlacement(hwnd)
    dpi, scale = get_window_dpi(hwnd)
    return {
        "hwnd": int(hwnd),
        "title": title,
        "process": _process_name(pid),
        "pid": int(pid),
        "rect": rect_dict(rect),
        "visible": bool(win32gui.IsWindowVisible(hwnd)),
        "minimized": bool(win32gui.IsIconic(hwnd)),
        "maximized": bool(user32.IsZoomed(hwnd)),
        "foreground": int(win32gui.GetForegroundWindow()) == int(hwnd),
        "show_state": int(placement[1]),
        "monitor": monitor_for_rect(rect),
        "dpi": dpi,
        "scale_factor": scale,
    }


def list_windows(
    title: str | None = None,
    process: str | None = None,
    pid: int | None = None,
    include_hidden: bool = False,
    include_untitled: bool = False,
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    title_pattern = re.compile(title, re.IGNORECASE) if title else None
    process_filter = process.casefold() if process else None

    def callback(hwnd: int, _extra: object) -> bool:
        try:
            item = window_info(hwnd)
            if not include_hidden and not item["visible"]:
                return True
            if not include_untitled and not item["title"].strip():
                return True
            if title_pattern and not title_pattern.search(item["title"]):
                return True
            if process_filter and process_filter not in item["process"].casefold():
                return True
            if pid is not None and item["pid"] != int(pid):
                return True
            result.append(item)
        except Exception:
            pass
        return True

    win32gui.EnumWindows(callback, None)
    result.sort(key=lambda item: (not item["foreground"], not item["visible"], item["title"].casefold()))
    return result


def foreground_window() -> dict[str, Any] | None:
    hwnd = int(win32gui.GetForegroundWindow())
    if not hwnd:
        return None
    try:
        return window_info(hwnd)
    except Exception:
        return None


def resolve_window(selector: dict[str, Any] | None = None) -> dict[str, Any]:
    selector = selector or {}
    hwnd = selector.get("hwnd")
    if hwnd:
        return window_info(int(hwnd))
    candidates = list_windows(
        title=selector.get("title"),
        process=selector.get("process"),
        pid=selector.get("pid"),
        include_hidden=True,
    )
    if not candidates:
        raise ValueError(f"No window matched selector: {selector}")
    if len(candidates) > 1 and not any(item.get("foreground") for item in candidates):
        raise ValueError(
            "Window selector is ambiguous; use hwnd or a narrower filter. "
            f"Matches: {[{'hwnd': x['hwnd'], 'title': x['title'], 'process': x['process']} for x in candidates[:10]]}"
        )
    return next((item for item in candidates if item["foreground"]), candidates[0])


def _force_foreground(hwnd: int) -> None:
    if win32gui.IsIconic(hwnd):
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    current = win32gui.GetForegroundWindow()
    current_thread = int(ctypes.windll.kernel32.GetCurrentThreadId())
    target_thread, _ = win32process.GetWindowThreadProcessId(hwnd)
    foreground_thread = win32process.GetWindowThreadProcessId(current)[0] if current else 0
    attached: list[int] = []
    try:
        for thread_id in {target_thread, foreground_thread}:
            if thread_id and thread_id != current_thread:
                if user32.AttachThreadInput(current_thread, thread_id, True):
                    attached.append(thread_id)
        win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
        win32gui.BringWindowToTop(hwnd)
        win32gui.SetForegroundWindow(hwnd)
        win32gui.SetWindowPos(
            hwnd, win32con.HWND_TOP, 0, 0, 0, 0,
            win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW,
        )
    finally:
        for thread_id in attached:
            user32.AttachThreadInput(current_thread, thread_id, False)


def focus_window(
    selector: dict[str, Any],
    action: str = "focus",
    x: int | None = None,
    y: int | None = None,
    width: int | None = None,
    height: int | None = None,
) -> dict[str, Any]:
    info = resolve_window(selector)
    hwnd = info["hwnd"]
    normalized = action.casefold()
    if normalized == "minimize":
        win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
    elif normalized == "maximize":
        win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
    elif normalized in {"restore", "focus", "front"}:
        if normalized == "restore":
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        _force_foreground(hwnd)
    elif normalized in {"move", "resize", "move_resize"}:
        current = info["rect"]
        target_x = int(x if x is not None else current["left"])
        target_y = int(y if y is not None else current["top"])
        target_width = int(width if width is not None else current["width"])
        target_height = int(height if height is not None else current["height"])
        if target_width < 100 or target_height < 60:
            raise ValueError("Window width must be >= 100 and height must be >= 60")
        win32gui.MoveWindow(hwnd, target_x, target_y, target_width, target_height, True)
        _force_foreground(hwnd)
    else:
        raise ValueError("action must be focus, front, restore, move, resize, move_resize, maximize, or minimize")
    time.sleep(0.12)
    return window_info(hwnd)
