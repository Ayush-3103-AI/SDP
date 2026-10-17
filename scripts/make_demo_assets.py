"""Generate the offline demo assets for the baseline CLI (T-0033).

Writes ``demo/frames/frame_*.png`` and ``demo/detections.json`` so that
``python -m xqi run --config config/baseline_demo.yaml --mode baseline`` runs
the whole loop with a fake printer, a replay frame source and a recorded
detector — no camera, no YOLO weights, no network.

Run once: ``python scripts/make_demo_assets.py``.
"""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

FRAME_COUNT = 8
# Six confirming frames of under_extrusion (config hits = 4).
PRESENT_FRAMES = range(6)
SIZE = (64, 64)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    frames_dir = root / "demo" / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    height, width = SIZE
    for index in range(FRAME_COUNT):
        image = np.full((height, width, 3), 30, dtype=np.uint8)
        cv2.rectangle(
            image,
            (8 + index, 8),
            (28 + index, 28),
            (0, 0, 200),
            thickness=-1,
        )
        created = cv2.imwrite(str(frames_dir / f"frame_{index:02d}.png"), image)
        if not created:
            raise SystemExit(f"could not write frame {index}")

    detections = {
        "frames": {
            str(index): [
                {
                    "cls": "under_extrusion",
                    "conf": 0.90,
                    "xyxy": [8, 8, 36, 36],
                }
            ]
            for index in PRESENT_FRAMES
        }
    }

    (root / "demo" / "detections.json").write_text(
        json.dumps(detections, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
