from pathlib import Path

import pytest

from windows_ui.control_state import ControlState


def test_pause_and_resume(tmp_path: Path) -> None:
    state = ControlState(tmp_path / "state.json")
    assert state.pause()["canInput"] is False
    assert state.resume()["canInput"] is True


def test_emergency_requires_local_resume(tmp_path: Path) -> None:
    state = ControlState(tmp_path / "state.json")
    state.emergency_stop()
    with pytest.raises(PermissionError):
        state.resume(local=False)
    assert state.resume(local=True)["state"] == "active"
