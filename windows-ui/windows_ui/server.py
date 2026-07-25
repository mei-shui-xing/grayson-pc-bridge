from __future__ import annotations

import atexit
import base64
import json
import sys
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import ImageContent, TextContent

from .audit import AUDIT
from .control_state import CONTROL
from .hotkey import EmergencyHotkey
from .input import execute_actions
from .local_control import LocalCommandWatcher
from .safety import assess_window
from .screenshot import CaptureResult, capture
from .tray import StatusTray
from .uia import snapshot_controls
from .wait import wait_for
from .windows import focus_window, foreground_window, list_windows, monitors, resolve_window


mcp = FastMCP(
    "AI Desktop Control Bridge Windows UI",
    instructions=(
        "Safety-gated Windows desktop tools. Read-only window/screenshot tools remain available while paused. "
        "Mouse, keyboard, focus, and window-management tools require an active control state and an allowlisted target. "
        "Emergency stop can only be cleared locally."
    ),
)


def _json_content(payload: dict[str, Any]) -> TextContent:
    return TextContent(type="text", text=json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str))


def _capture_content(result: CaptureResult, extra: dict[str, Any] | None = None) -> list[TextContent | ImageContent]:
    payload = result.as_payload()
    if extra:
        payload.update(extra)
    return [
        _json_content(payload),
        ImageContent(type="image", data=base64.b64encode(result.data).decode("ascii"), mimeType=result.mime_type),
    ]


@mcp.tool(name="desktop_list_windows")
def desktop_list_windows(
    title: str | None = None,
    process: str | None = None,
    pid: int | None = None,
    include_hidden: bool = False,
    include_untitled: bool = False,
) -> dict[str, Any]:
    """List top-level Windows windows with process, PID, physical-pixel bounds, visibility, state, foreground flag, DPI, and monitor. Filters are optional regex/title substring, process, and PID."""
    values = list_windows(title, process, pid, include_hidden, include_untitled)
    return {"windows": values, "count": len(values), "foreground": foreground_window(), "monitors": monitors()}


@mcp.tool(name="desktop_focus_window")
def desktop_focus_window(
    window: dict[str, Any],
    action: str = "focus",
    x: int | None = None,
    y: int | None = None,
    width: int | None = None,
    height: int | None = None,
) -> dict[str, Any]:
    """Focus, restore, front, move, resize, maximize, or minimize an allowlisted window. Closing windows is intentionally unsupported."""
    CONTROL.require_input()
    target = resolve_window(window)
    decision = assess_window(target)
    if not decision["allowed"]:
        AUDIT.write({"action_type": "focus_window", "target": target, "success": False, "refused_reason": decision["reason"], "safety_intercept": True})
        raise PermissionError(decision["reason"])
    result = focus_window(window, action, x, y, width, height)
    AUDIT.write({"action_type": f"window_{action}", "target": result, "success": True, "refused_reason": None, "safety_intercept": False})
    return {"success": True, "window": result}


@mcp.tool(name="desktop_screenshot", structured_output=False)
def desktop_screenshot(
    target: str = "full",
    window: dict[str, Any] | None = None,
    monitor: int | None = None,
    region: dict[str, int] | None = None,
    format: str = "webp",
    quality: int = 78,
    backend: str = "auto",
) -> list[TextContent | ImageContent]:
    """Capture the full virtual desktop, one monitor, one visible window, or a physical-pixel rectangle. Uses dxcam first, then mss and Pillow. Returns image plus DPI/monitor/cursor/foreground metadata."""
    return _capture_content(capture(target, window, monitor, region, format, quality, backend))


@mcp.tool(name="desktop_action", structured_output=False)
def desktop_action(
    actions: list[dict[str, Any]],
    screenshot_after: bool = False,
    screenshot_format: str = "webp",
) -> dict[str, Any] | list[TextContent | ImageContent]:
    """Execute one or more gated mouse/keyboard actions: move, click, double_click, right_click, mouse_down, mouse_up, drag, scroll, type_text, press_key, hotkey, wait. The batch aborts as soon as focus leaves the allowlist."""
    result = execute_actions(actions)
    if screenshot_after:
        shot = capture(target="full", image_format=screenshot_format, quality=78)
        return _capture_content(shot, {"action_result": result})
    return result


@mcp.tool(name="desktop_snapshot", structured_output=False)
def desktop_snapshot(
    window: dict[str, Any] | None = None,
    include_screenshot: bool = True,
    max_nodes: int | None = None,
    max_depth: int | None = None,
    screenshot_format: str = "webp",
) -> dict[str, Any] | list[TextContent | ImageContent]:
    """Return a pruned UI Automation tree for the active or selected window, with numbered interactive controls and an optional screenshot. Custom-canvas apps may expose few UIA nodes; screenshots remain usable."""
    snap = snapshot_controls(window, max_nodes, max_depth)
    if include_screenshot:
        shot = capture(target="window", window={"hwnd": snap["window"]["hwnd"]}, image_format=screenshot_format, quality=80)
        return _capture_content(shot, {"uia": snap})
    return snap


@mcp.tool(name="desktop_wait_for", structured_output=False)
def desktop_wait_for(
    condition: dict[str, Any],
    timeout_ms: int = 15000,
    interval_ms: int = 250,
    screenshot_on_timeout: bool = True,
) -> dict[str, Any] | list[TextContent | ImageContent]:
    """Wait for a window/process/control/text/foreground/region-change condition without fixed sleeps. Set condition.type to window_appears, window_disappears, control_appears, text_appears, process_starts, process_ends, region_changed, or foreground_changes."""
    result = wait_for(condition, timeout_ms, interval_ms, screenshot_on_timeout)
    if result.screenshot:
        return _capture_content(result.screenshot, {"wait_result": result.payload})
    return result.payload


@mcp.tool(name="desktop_control_status")
def desktop_control_status() -> dict[str, Any]:
    """Read the local remote-input state. Screenshots/window reads work in every state; mouse and keyboard require state=active."""
    return {**CONTROL.status(), "foreground": foreground_window()}


@mcp.tool(name="desktop_pause_control")
def desktop_pause_control(reason: str = "remote pause request") -> dict[str, Any]:
    """Pause all remote mouse and keyboard operations while leaving read-only tools available."""
    return CONTROL.pause(reason)


@mcp.tool(name="desktop_resume_control")
def desktop_resume_control() -> dict[str, Any]:
    """Resume from a normal pause. This cannot clear a local emergency stop; emergency recovery must be confirmed locally."""
    return CONTROL.resume(local=False)


HOTKEY = EmergencyHotkey()
TRAY = StatusTray()
LOCAL_COMMANDS = LocalCommandWatcher()


def _shutdown() -> None:
    LOCAL_COMMANDS.stop()
    HOTKEY.stop()
    TRAY.stop()


def main() -> None:
    try:
        HOTKEY.start()
        TRAY.start()
        LOCAL_COMMANDS.start()
        atexit.register(_shutdown)
        print("AI Desktop Control Bridge Windows UI sidecar ready", file=sys.stderr, flush=True)
        mcp.run(transport="stdio")
    finally:
        _shutdown()


if __name__ == "__main__":
    main()
