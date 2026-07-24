from __future__ import annotations

import json
import sys

import dxcam
from PIL import Image


def main() -> int:
    payload = json.loads(sys.argv[1])
    camera = dxcam.create(
        output_idx=int(payload["output_idx"]),
        output_color="RGB",
        processor_backend="numpy",
    )
    try:
        frame = None
        for _ in range(3):
            frame = camera.grab(region=tuple(payload["region"]))
            if frame is not None:
                break
        if frame is None:
            raise RuntimeError("dxcam returned no frame")
        Image.fromarray(frame, mode="RGB").save(payload["output"], "PNG")
        return 0
    finally:
        camera.release()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
