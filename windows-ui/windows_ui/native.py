from __future__ import annotations

import ctypes
from ctypes import wintypes


user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
shcore = ctypes.windll.shcore


def enable_dpi_awareness() -> None:
    try:
        # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2
        user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except Exception:
        try:
            shcore.SetProcessDpiAwareness(2)
        except Exception:
            user32.SetProcessDPIAware()


enable_dpi_awareness()


def rect_dict(rect: tuple[int, int, int, int]) -> dict[str, int]:
    left, top, right, bottom = rect
    return {
        "left": int(left),
        "top": int(top),
        "right": int(right),
        "bottom": int(bottom),
        "width": max(0, int(right - left)),
        "height": max(0, int(bottom - top)),
    }


def get_window_dpi(hwnd: int) -> tuple[int, float]:
    try:
        dpi = int(user32.GetDpiForWindow(hwnd)) or 96
    except Exception:
        dpi = 96
    return dpi, round(dpi / 96.0, 4)


def get_cursor_position() -> tuple[int, int]:
    point = wintypes.POINT()
    if not user32.GetCursorPos(ctypes.byref(point)):
        raise ctypes.WinError()
    return int(point.x), int(point.y)


def root_window_from_point(x: int, y: int) -> int:
    point = wintypes.POINT(x, y)
    hwnd = int(user32.WindowFromPoint(point))
    return int(user32.GetAncestor(hwnd, 2)) if hwnd else 0  # GA_ROOT
