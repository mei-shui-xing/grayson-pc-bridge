from windows_ui.safety import assess_window


def window(process: str, title: str) -> dict:
    return {"process": process, "title": title, "pid": 1, "hwnd": 1}


def test_allows_configured_editor() -> None:
    assert assess_window(window("Code.exe", "project - Visual Studio Code"))["allowed"] is True


def test_forbidden_process_overrides_everything() -> None:
    decision = assess_window(window("WeChat.exe", "SchoolSim"))
    assert decision["allowed"] is False
    assert decision["safety_intercept"] is True


def test_browser_payment_title_is_blocked() -> None:
    decision = assess_window(window("msedge.exe", "Payment - Example Shop"))
    assert decision["allowed"] is False


def test_terminal_requires_project_title() -> None:
    assert assess_window(window("powershell.exe", "Administrator: Windows PowerShell"))["allowed"] is False
    assert assess_window(window("powershell.exe", "Grayson-PC-Bridge"))["allowed"] is True
