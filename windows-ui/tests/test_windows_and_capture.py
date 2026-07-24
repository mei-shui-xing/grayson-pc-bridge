from windows_ui.screenshot import capture
from windows_ui.windows import list_windows, monitors


def test_lists_monitors_and_windows() -> None:
    assert monitors()
    assert isinstance(list_windows(), list)


def test_mss_region_capture_has_physical_size() -> None:
    result = capture(
        target="region",
        region={"left": 0, "top": 0, "width": 160, "height": 100},
        image_format="png",
        backend="mss",
    )
    assert result.image.size == (160, 100)
    assert result.metadata["capture_region"]["width"] == 160
    assert result.metadata["display_scales"]
    assert result.mime_type == "image/png"


def test_auto_capture_prefers_dxcam_or_reports_fallback() -> None:
    result = capture(
        target="region",
        region={"left": 0, "top": 0, "width": 120, "height": 80},
        image_format="jpeg",
        backend="auto",
    )
    assert result.metadata["backend"] in {"dxcam", "mss", "pillow"}
    if result.metadata["backend"] != "dxcam":
        assert result.metadata["fallback_errors"]
