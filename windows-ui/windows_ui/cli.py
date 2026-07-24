from __future__ import annotations

import argparse
import json

from .config import RUNTIME_DIR
from .local_control import send_local_command


def main() -> int:
    parser = argparse.ArgumentParser(description="Local control commands for Grayson Windows UI")
    parser.add_argument("action", choices=["status", "pause", "resume", "emergency"])
    args = parser.parse_args()
    if args.action == "status":
        path = RUNTIME_DIR / "ui-status.json"
        try:
            print(path.read_text(encoding="utf-8"))
            return 0
        except OSError as error:
            print(json.dumps({"success": False, "error": str(error)}, ensure_ascii=False))
            return 1
    result = send_local_command(args.action)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
