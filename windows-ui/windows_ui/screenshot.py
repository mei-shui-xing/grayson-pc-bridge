from __future__ import annotations

import base64
import ctypes
import io
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from PIL import Image, ImageGrab

from .native import get_cursor_position, rect_dict, shcore
from .windows import foreground_window, monitors, resolve_window


@dataclass(slots=True)
class CaptureResult:
    image: Image.Image
    metadata: dict[str, Any]
    mime_type: str
    data: bytes

    def as_payload(self, include_base64: bool = False) -> dict[str, Any]:
        payload = dict(self.metadata)
        payload["mime_type"] = self.mime_type
        payload["encoded_bytes"] = len(self.data)
        if include_base64:
            payload["image_base64"] = base64.b64encode(self.data).decode("ascii")
        return payload


def _monitor_scales() -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for item in monitors():
        dpi_x = ctypes.c_uint(96)
        dpi_y = ctypes.c_uint(96)
        try:
            shcore.GetDpiForMonitor(item["handle"], 0, ctypes.byref(dpi_x), ctypes.byref(dpi_y))
        except Exception:
            pass
        result.append({
            "index": item["index"],
            "device": item["device"],
            "dpi": int(dpi_x.value),
            "scale_factor": round(dpi_x.value / 96.0, 4),
            "bounds": item["bounds"],
        })
    return result


def _find_containing_monitor(rect: tuple[int, int, int, int]) -> dict[str, Any] | None:
    left, top, right, bottom = rect
    for item in monitors():
        bounds = item["bounds"]
        if left >= bounds["left"] and top >= bounds["top"] and right <= bounds["right"] and bottom <= bounds["bottom"]:
            return item
    return None


def _capture_dxcam(rect: tuple[int, int, int, int]) -> Image.Image:
    monitor = _find_containing_monitor(rect)
    if monitor is None:
        raise RuntimeError("dxcam capture region crosses monitor boundaries")
    bounds = monitor["bounds"]
    local = (
        rect[0] - bounds["left"], rect[1] - bounds["top"],
        rect[2] - bounds["left"], rect[3] - bounds["top"],
    )
    # DXGI/COM capture is isolated in a short-lived main-thread subprocess.
    # FastMCP runs synchronous tools in worker threads; constructing DXcam's
    # global COM factory in one of those threads can terminate the interpreter
    # instead of raising a Python exception on some GPU drivers.
    handle, temp_name = tempfile.mkstemp(prefix="ai-desktop-control-bridge-dxcam-", suffix=".png")
    os.close(handle)
    try:
        completed = subprocess.run(
            [
                sys.executable, "-m", "windows_ui.dxcam_capture",
                json.dumps({"output_idx": int(monitor["index"]), "region": local, "output": temp_name}),
            ],
            capture_output=True,
            text=True,
            timeout=8,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "unknown dxcam failure").strip()
            raise RuntimeError(detail[-1000:])
        with Image.open(temp_name) as captured:
            return captured.convert("RGB").copy()
    finally:
        try:
            os.unlink(temp_name)
        except OSError:
            pass


def _capture_mss(rect: tuple[int, int, int, int]) -> Image.Image:
    import mss

    left, top, right, bottom = rect
    with mss.MSS() as grabber:
        shot = grabber.grab({"left": left, "top": top, "width": right - left, "height": bottom - top})
        return Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")


def _capture_pillow(rect: tuple[int, int, int, int]) -> Image.Image:
    return ImageGrab.grab(bbox=rect, all_screens=True).convert("RGB")


def _encode(image: Image.Image, image_format: str, quality: int) -> tuple[bytes, str]:
    fmt = image_format.casefold()
    output = io.BytesIO()
    if fmt == "png":
        image.save(output, "PNG", optimize=True)
        return output.getvalue(), "image/png"
    if fmt in {"jpg", "jpeg"}:
        image.convert("RGB").save(output, "JPEG", quality=max(30, min(quality, 95)), optimize=True)
        return output.getvalue(), "image/jpeg"
    if fmt == "webp":
        image.convert("RGB").save(output, "WEBP", quality=max(30, min(quality, 95)), method=4)
        return output.getvalue(), "image/webp"
    raise ValueError("format must be webp, jpeg, or png")


def capture(
    target: str = "full",
    window: dict[str, Any] | None = None,
    monitor: int | None = None,
    region: dict[str, int] | None = None,
    image_format: str = "webp",
    quality: int = 78,
    backend: str = "auto",
) -> CaptureResult:
    target = target.casefold()
    window_info: dict[str, Any] | None = None
    all_monitors = monitors()
    if not all_monitors:
        raise RuntimeError("No displays were detected")

    if target == "window":
        window_info = resolve_window(window)
        if window_info["minimized"]:
            raise ValueError("Cannot capture a minimized window; restore it first")
        r = window_info["rect"]
        rect = (r["left"], r["top"], r["right"], r["bottom"])
    elif target == "monitor":
        index = int(0 if monitor is None else monitor)
        match = next((item for item in all_monitors if item["index"] == index), None)
        if not match:
            raise ValueError(f"Monitor index {index} does not exist")
        r = match["bounds"]
        rect = (r["left"], r["top"], r["right"], r["bottom"])
    elif target == "region":
        if not region:
            raise ValueError("region is required for target=region")
        left = int(region.get("left", region.get("x", 0)))
        top = int(region.get("top", region.get("y", 0)))
        width = int(region.get("width", 0))
        height = int(region.get("height", 0))
        if width <= 0 or height <= 0:
            raise ValueError("region width and height must be positive")
        rect = (left, top, left + width, top + height)
    elif target == "full":
        left = min(item["bounds"]["left"] for item in all_monitors)
        top = min(item["bounds"]["top"] for item in all_monitors)
        right = max(item["bounds"]["right"] for item in all_monitors)
        bottom = max(item["bounds"]["bottom"] for item in all_monitors)
        rect = (left, top, right, bottom)
    else:
        raise ValueError("target must be full, monitor, window, or region")

    if rect[2] <= rect[0] or rect[3] <= rect[1]:
        raise ValueError(f"Invalid capture rectangle: {rect}")

    attempts = [backend.casefold()] if backend.casefold() != "auto" else ["dxcam", "mss", "pillow"]
    image: Image.Image | None = None
    errors: list[str] = []
    used_backend = ""
    for candidate in attempts:
        try:
            if candidate == "dxcam":
                image = _capture_dxcam(rect)
            elif candidate == "mss":
                image = _capture_mss(rect)
            elif candidate == "pillow":
                image = _capture_pillow(rect)
            else:
                raise ValueError("backend must be auto, dxcam, mss, or pillow")
            used_backend = candidate
            break
        except Exception as error:
            errors.append(f"{candidate}: {error}")
    if image is None:
        raise RuntimeError("All screenshot backends failed: " + " | ".join(errors))

    data, mime = _encode(image, image_format, quality)
    cursor_x, cursor_y = get_cursor_position()
    active = foreground_window()
    metadata = {
        "target": target,
        "backend": used_backend,
        "fallback_errors": errors,
        "pixel_size": {"width": image.width, "height": image.height},
        "capture_region": rect_dict(rect),
        "display_scales": _monitor_scales(),
        "window_scale_factor": window_info.get("scale_factor") if window_info else None,
        "cursor": {"x": cursor_x, "y": cursor_y},
        "foreground_window": active,
        "captured_window": window_info,
        "captured_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="milliseconds"),
    }
    return CaptureResult(image=image, metadata=metadata, mime_type=mime, data=data)
