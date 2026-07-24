from __future__ import annotations

import json

from .screenshot import capture
from .windows import monitors


def screenshot_health() -> dict[str, object]:
    displays = monitors()
    if not displays:
        raise RuntimeError("No displays were detected")

    bounds = displays[0]["bounds"]
    result = capture(
        target="region",
        region={
            "left": int(bounds["left"]),
            "top": int(bounds["top"]),
            "width": min(16, int(bounds["right"]) - int(bounds["left"])),
            "height": min(16, int(bounds["bottom"]) - int(bounds["top"])),
        },
        image_format="png",
        backend="auto",
    )
    return {
        "ok": True,
        "backend": result.metadata["backend"],
        "pixelSize": result.metadata["pixel_size"],
        "fallbackErrors": result.metadata["fallback_errors"],
    }


def main() -> None:
    print(json.dumps(screenshot_health(), ensure_ascii=False))


if __name__ == "__main__":
    main()
