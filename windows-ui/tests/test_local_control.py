from __future__ import annotations

import os
import subprocess
import sys


def test_cli_import_does_not_claim_server_runtime(tmp_path) -> None:
    env = os.environ.copy()
    env["WINDOWS_UI_RUNTIME_DIR"] = str(tmp_path)

    result = subprocess.run(
        [sys.executable, "-c", "import windows_ui.cli"],
        check=False,
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert not (tmp_path / "ui-status.json").exists()
