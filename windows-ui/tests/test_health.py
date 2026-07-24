from windows_ui.health import screenshot_health


def test_screenshot_health(monkeypatch):
    monkeypatch.setattr(
        "windows_ui.health.monitors",
        lambda: [{"bounds": {"left": 10, "top": 20, "right": 110, "bottom": 220}}],
    )

    class Result:
        metadata = {
            "backend": "pillow",
            "pixel_size": {"width": 16, "height": 16},
            "fallback_errors": [],
        }

    def fake_capture(**kwargs):
        assert kwargs["region"] == {"left": 10, "top": 20, "width": 16, "height": 16}
        return Result()

    monkeypatch.setattr("windows_ui.health.capture", fake_capture)
    assert screenshot_health() == {
        "ok": True,
        "backend": "pillow",
        "pixelSize": {"width": 16, "height": 16},
        "fallbackErrors": [],
    }
