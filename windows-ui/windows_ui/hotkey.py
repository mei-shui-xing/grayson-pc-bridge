from __future__ import annotations

import ctypes
import threading
from ctypes import wintypes

from .config import SETTINGS, _normalize_hotkey
from .control_state import CONTROL
from .native import kernel32, user32


MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
VK_MAP = {"PAUSE": 0x13, "F12": 0x7B}
MOD_MAP = {"ALT": MOD_ALT, "CTRL": MOD_CONTROL, "SHIFT": MOD_SHIFT, "WIN": MOD_WIN}


class EmergencyHotkey:
    def __init__(self) -> None:
        self.thread_id: int | None = None
        self.hotkey_id = 0xB317
        self.registered = threading.Event()
        self.thread = threading.Thread(target=self._run, name="windows-ui-emergency-hotkey", daemon=True)

    def start(self) -> None:
        self.thread.start()
        self.registered.wait(2)

    def stop(self) -> None:
        if self.thread_id:
            user32.PostThreadMessageW(self.thread_id, WM_QUIT, 0, 0)

    @staticmethod
    def _parse(value: str) -> tuple[int, int]:
        parts = _normalize_hotkey(value).split("+")
        modifiers = MOD_NOREPEAT
        key = 0
        for part in parts:
            if part in MOD_MAP:
                modifiers |= MOD_MAP[part]
            else:
                key = VK_MAP.get(part, ord(part) if len(part) == 1 else 0)
        if not key:
            raise ValueError(f"Unsupported emergency hotkey: {value}")
        return modifiers, key

    def _run(self) -> None:
        self.thread_id = int(kernel32.GetCurrentThreadId())
        selected = SETTINGS.emergency_hotkey
        try:
            modifiers, key = self._parse(selected)
            if not user32.RegisterHotKey(None, self.hotkey_id, modifiers, key):
                selected = SETTINGS.emergency_hotkey_fallback
                modifiers, key = self._parse(selected)
                if not user32.RegisterHotKey(None, self.hotkey_id, modifiers, key):
                    raise ctypes.WinError()
            CONTROL.set_hotkey(selected)
            self.registered.set()
            message = wintypes.MSG()
            while user32.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
                if message.message == WM_HOTKEY and message.wParam == self.hotkey_id:
                    CONTROL.emergency_stop(f"local emergency hotkey {selected}")
        except Exception as error:
            CONTROL.set_error(f"Emergency hotkey registration failed: {error}")
            self.registered.set()
        finally:
            user32.UnregisterHotKey(None, self.hotkey_id)
