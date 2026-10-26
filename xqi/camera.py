from __future__ import annotations

import time
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

from xqi.types import Frame

IMAGE_SUFFIXES = {".bmp", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp"}


def open_source(spec: str, width: int, height: int) -> Iterator[Frame]:
    """Yield frames from a camera index ("0") or a folder ("replay:<dir>[@<fps>]")."""
    if spec.startswith("replay:"):
        folder, _, fps = spec.removeprefix("replay:").rpartition("@")
        if not folder:  # no "@<fps>" suffix
            folder, fps = fps, ""
        images = _replay(Path(folder), float(fps) if fps else None)
    elif spec.isdigit():
        images = _camera(int(spec), width, height)
    else:
        raise ValueError(f"unknown camera source: {spec!r}")

    last_ts = float("-inf")
    for frame_id, image in enumerate(images):
        # Windows monotonic ticks every ~15.6 ms; nudge so ts strictly increases.
        last_ts = max(time.monotonic(), last_ts + 1e-6)
        yield Frame(frame_id, last_ts, _wall_iso(), image)


def _camera(index: int, width: int, height: int) -> Iterator[np.ndarray]:
    capture = cv2.VideoCapture(index)
    if not capture.isOpened():
        raise RuntimeError(f"cannot open camera {index}")
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    try:
        while True:
            ok, image = capture.read()
            if ok:  # failed reads are skipped; the loop's max_gap_s handles stalls
                yield image
    finally:
        capture.release()


def _replay(folder: Path, fps: float | None) -> Iterator[np.ndarray]:
    if not folder.is_dir():
        raise FileNotFoundError(f"replay folder not found: {folder}")
    paths = sorted(p for p in folder.iterdir() if p.suffix.lower() in IMAGE_SUFFIXES)
    start = time.perf_counter()  # finer than monotonic on Windows
    for i, path in enumerate(paths):
        image = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if image is None:
            continue
        if fps:
            time.sleep(max(0.0, start + i / fps - time.perf_counter()))
        yield image


def _wall_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="milliseconds")
