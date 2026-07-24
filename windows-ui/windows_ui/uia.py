from __future__ import annotations

import re
from typing import Any

import pythoncom
from pywinauto import Desktop

from .config import SETTINGS
from .native import rect_dict
from .windows import resolve_window


PRIORITY_TYPES = {
    "Button", "Edit", "MenuItem", "Tab", "TabItem", "ListItem", "TreeItem",
    "CheckBox", "ComboBox", "Slider", "Hyperlink", "RadioButton", "Document",
    "ScrollBar", "SplitButton", "DataItem",
}
CLICKABLE_TYPES = {
    "Button", "MenuItem", "Tab", "TabItem", "ListItem", "TreeItem", "CheckBox",
    "ComboBox", "Slider", "Hyperlink", "RadioButton", "SplitButton", "DataItem",
}
INPUT_TYPES = {"Edit", "Document", "ComboBox"}
SCROLLABLE_TYPES = {"List", "Tree", "DataGrid", "Document", "Pane", "ScrollBar"}


def _rectangle(info: Any) -> dict[str, int]:
    rect = info.rectangle
    return rect_dict((rect.left, rect.top, rect.right, rect.bottom))


def _safe(value: Any, default: Any = None) -> Any:
    try:
        return value() if callable(value) else value
    except Exception:
        return default


def _node_payload(info: Any, node_id: int, parent_id: int | None, depth: int) -> dict[str, Any]:
    control_type = str(_safe(lambda: info.control_type, ""))
    name = str(_safe(lambda: info.name, "") or "")
    enabled = bool(_safe(lambda: info.enabled, False))
    visible = bool(_safe(lambda: info.visible, False))
    return {
        "id": node_id,
        "parent_id": parent_id,
        "depth": depth,
        "name": name[:500],
        "control_type": control_type,
        "automation_id": str(_safe(lambda: info.automation_id, "") or "")[:200],
        "class_name": str(_safe(lambda: info.class_name, "") or "")[:200],
        "rect": _rectangle(info),
        "enabled": enabled,
        "visible": visible,
        "focused": bool(_safe(lambda: info.has_keyboard_focus, False)),
        "is_password": bool(_safe(lambda: info.is_password, False)),
        "clickable": enabled and visible and control_type in CLICKABLE_TYPES,
        "input": enabled and visible and control_type in INPUT_TYPES and not bool(_safe(lambda: info.is_password, False)),
        "scrollable": enabled and visible and control_type in SCROLLABLE_TYPES,
    }


def snapshot_controls(
    window: dict[str, Any] | None = None,
    max_nodes: int | None = None,
    max_depth: int | None = None,
) -> dict[str, Any]:
    pythoncom.CoInitialize()
    try:
        target = resolve_window(window)
        wrapper = Desktop(backend="uia").window(handle=target["hwnd"]).wrapper_object()
        root = wrapper.element_info
        limit = max(1, min(int(max_nodes or SETTINGS.max_snapshot_nodes), 1000))
        depth_limit = max(1, min(int(max_depth or SETTINGS.max_snapshot_depth), 20))
        controls: list[dict[str, Any]] = []
        scanned = 0
        truncated = False

        def walk(info: Any, depth: int, retained_parent: int | None, is_root: bool = False) -> None:
            nonlocal scanned, truncated
            if truncated or depth > depth_limit:
                return
            scanned += 1
            control_type = str(_safe(lambda: info.control_type, ""))
            name = str(_safe(lambda: info.name, "") or "")
            enabled = bool(_safe(lambda: info.enabled, False))
            visible = bool(_safe(lambda: info.visible, False))
            retain = is_root or control_type in PRIORITY_TYPES or (
                enabled and visible and control_type not in {"Pane", "Group", "Text", "Custom", "Window"} and bool(name)
            )
            current_parent = retained_parent
            if retain:
                if len(controls) >= limit:
                    truncated = True
                    return
                node_id = len(controls) + 1
                controls.append(_node_payload(info, node_id, retained_parent, depth))
                current_parent = node_id
            try:
                children = info.children()
            except Exception:
                children = []
            for child in children:
                walk(child, depth + 1, current_parent)
                if truncated:
                    break

        walk(root, 0, None, True)
        return {
            "window": target,
            "controls": controls,
            "control_count": len(controls),
            "scanned_nodes": scanned,
            "truncated": truncated,
            "max_nodes": limit,
            "max_depth": depth_limit,
        }
    finally:
        pythoncom.CoUninitialize()


def control_exists(
    name: str | None = None,
    control_type: str | None = None,
    window: dict[str, Any] | None = None,
) -> bool:
    snap = snapshot_controls(window=window, max_nodes=500, max_depth=12)
    name_pattern = re.compile(name, re.IGNORECASE) if name else None
    for control in snap["controls"]:
        if name_pattern and not name_pattern.search(control["name"]):
            continue
        if control_type and control["control_type"].casefold() != control_type.casefold():
            continue
        return True
    return False


def text_exists(text: str, window: dict[str, Any] | None = None) -> bool:
    pythoncom.CoInitialize()
    try:
        target = resolve_window(window)
        wrapper = Desktop(backend="uia").window(handle=target["hwnd"]).wrapper_object()
        pattern = re.compile(text, re.IGNORECASE)
        for candidate in [wrapper, *wrapper.descendants()]:
            try:
                if pattern.search(candidate.window_text() or ""):
                    return True
            except Exception:
                continue
        return False
    finally:
        pythoncom.CoUninitialize()
