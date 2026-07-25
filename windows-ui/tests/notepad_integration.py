from __future__ import annotations

import asyncio
import base64
import json
import os
import subprocess
import time
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "notepad-phase-a.txt"
RESULTS = ROOT / "test-results"
RUNTIME = ROOT / "test-results" / "runtime"
TEST_LINE = "Windows UI 自动化阶段 A 测试通过"


def parse_text(result) -> dict:
    for item in result.content:
        if item.type == "text":
            return json.loads(item.text)
    raise AssertionError("Tool returned no JSON text content")


async def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    RUNTIME.mkdir(parents=True, exist_ok=True)
    original = "AI Desktop Control Bridge Windows UI Phase A\n"
    FIXTURE.write_text(original, encoding="utf-8")
    notepad = subprocess.Popen(["notepad.exe", str(FIXTURE)])
    try:
        env = {
            **os.environ,
            "WINDOWS_UI_ROOT": str(ROOT),
            "WINDOWS_UI_RUNTIME_DIR": str(RUNTIME),
            "WINDOWS_UI_LOG_DIR": str(RESULTS),
        }
        params = StdioServerParameters(
            command=str(ROOT / ".venv" / "Scripts" / "python.exe"),
            args=["-m", "windows_ui.server"],
            cwd=str(ROOT),
            env=env,
        )
        async with stdio_client(params) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                await session.initialize()
                waited = await session.call_tool("desktop_wait_for", {
                    "condition": {"type": "window_appears", "window": {"process": "notepad.exe", "title": "notepad-phase-a"}},
                    "timeout_ms": 15000,
                    "interval_ms": 250,
                })
                assert parse_text(waited)["matched"] is True
                listed = await session.call_tool("desktop_list_windows", {"process": "notepad.exe", "title": "notepad-phase-a"})
                windows = parse_text(listed)["windows"]
                assert windows
                target = windows[0]
                focused = await session.call_tool("desktop_focus_window", {"window": {"hwnd": target["hwnd"]}})
                assert parse_text(focused)["success"] is True
                snapshot = await session.call_tool("desktop_snapshot", {
                    "window": {"hwnd": target["hwnd"]},
                    "include_screenshot": False,
                    "max_nodes": 120,
                    "max_depth": 8,
                })
                snapshot_payload = parse_text(snapshot)
                assert snapshot_payload["controls"]
                edit_x = target["rect"]["left"] + max(160, target["rect"]["width"] // 3)
                edit_y = target["rect"]["top"] + max(160, target["rect"]["height"] // 3)
                pointer_action = await session.call_tool("desktop_action", {
                    "actions": [
                        {"type": "click", "x": edit_x, "y": edit_y},
                        {"type": "scroll", "x": edit_x, "y": edit_y, "amount": -1},
                        {
                            "type": "drag",
                            "from_x": edit_x,
                            "from_y": edit_y,
                            "x": edit_x + 40,
                            "y": edit_y,
                            "duration": 0.12,
                        },
                    ],
                })
                assert parse_text(pointer_action)["success"] is True
                action = await session.call_tool("desktop_action", {
                    "actions": [
                        {"type": "hotkey", "keys": ["CTRL", "END"]},
                        {"type": "press_key", "key": "ENTER"},
                        {"type": "type_text", "text": TEST_LINE},
                        {"type": "hotkey", "keys": ["CTRL", "S"]},
                        {"type": "wait", "milliseconds": 300},
                    ],
                    "screenshot_after": True,
                    "screenshot_format": "png",
                })
                action_payload = parse_text(action)
                assert action_payload["action_result"]["success"] is True
                for item in action.content:
                    if item.type == "image":
                        (RESULTS / "notepad-after.png").write_bytes(base64.b64decode(item.data))
                        break
                assert TEST_LINE in FIXTURE.read_text(encoding="utf-8")

                paused = await session.call_tool("desktop_pause_control", {"reason": "Phase A refusal test"})
                assert parse_text(paused)["state"] == "paused"
                click_x = target["rect"]["left"] + 80
                click_y = target["rect"]["top"] + 80
                refused = await session.call_tool("desktop_action", {
                    "actions": [{"type": "click", "x": click_x, "y": click_y}],
                })
                refused_payload = parse_text(refused)
                assert refused_payload["success"] is False
                assert "disabled" in refused_payload["abort_reason"].casefold()
                read_while_paused = await session.call_tool("desktop_screenshot", {
                    "target": "window", "window": {"hwnd": target["hwnd"]}, "format": "jpeg", "quality": 55,
                })
                assert any(item.type == "image" for item in read_while_paused.content)
                resumed = await session.call_tool("desktop_resume_control", {})
                assert parse_text(resumed)["state"] == "active"
                print(json.dumps({
                    "success": True,
                    "window": {"hwnd": target["hwnd"], "title": target["title"], "dpi": target["dpi"], "scale_factor": target["scale_factor"]},
                    "uia_control_count": len(snapshot_payload["controls"]),
                    "click_scroll_drag_verified": True,
                    "typed_text_verified": True,
                    "save_verified": True,
                    "pause_refusal_verified": True,
                    "screenshot_while_paused_verified": True,
                    "screenshot": str(RESULTS / "notepad-after.png"),
                }, ensure_ascii=False, indent=2))
    finally:
        time.sleep(0.3)
        notepad.terminate()
        try:
            notepad.wait(timeout=5)
        except subprocess.TimeoutExpired:
            notepad.kill()


if __name__ == "__main__":
    asyncio.run(main())
