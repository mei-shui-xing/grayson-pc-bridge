from __future__ import annotations

import threading
from typing import Any

import pystray
from PIL import Image, ImageDraw

from .control_state import CONTROL


COLORS = {"active": "#22c55e", "paused": "#eab308", "emergency": "#ef4444"}
LABELS = {"active": "绿色：允许远程控制", "paused": "黄色：只允许查看", "emergency": "红色：已停止"}


def _image(state: str) -> Image.Image:
    image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((5, 5, 59, 59), fill=COLORS.get(state, "#6b7280"), outline="white", width=4)
    draw.rectangle((29, 18, 35, 45), fill="white")
    return image


class StatusTray:
    def __init__(self) -> None:
        initial = CONTROL.status()
        self.icon = pystray.Icon(
            "GraysonComputerAssistant",
            _image(initial["state"]),
            f"Grayson电脑助手 - {LABELS[initial['state']]}",
            menu=pystray.Menu(
                pystray.MenuItem("暂停远程输入", self._pause),
                pystray.MenuItem("本地恢复控制", self._resume),
                pystray.MenuItem("紧急停止", self._emergency),
            ),
        )
        CONTROL.subscribe(self._state_changed)
        self.thread = threading.Thread(target=self.icon.run, name="windows-ui-tray", daemon=True)

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        try:
            self.icon.stop()
        except Exception:
            pass

    def _state_changed(self, status: dict[str, Any]) -> None:
        state = status["state"]
        self.icon.icon = _image(state)
        self.icon.title = f"Grayson电脑助手 - {LABELS[state]}"
        if state == "emergency":
            try:
                self.icon.notify("远程鼠标键盘已紧急停止。只能在本机恢复。", "Grayson电脑助手")
            except Exception:
                pass

    @staticmethod
    def _pause(_icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        CONTROL.pause("local tray pause")

    @staticmethod
    def _resume(_icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        CONTROL.resume(local=True)

    @staticmethod
    def _emergency(_icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        CONTROL.emergency_stop("local tray emergency stop")
