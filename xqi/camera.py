"""Frame sources: a live camera index or a recorded replay folder (T-0029).

``open_source`` yields the canonical :class:`xqi.types.Frame` (BGR uint8, ``ts``
from ``time.monotonic()``, ``frame_id`` from 0). The replay source makes the
whole visual pipeline runnable offline with checked-in images; the camera
source is only opened when an integer index is configured and is covered by a
hardware-marked test.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import cv2

from xqi.types import Frame

_IMAGE_SUFFIXES = frozenset(
    {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}
)
_REPLAY_PREFIX = "replay:"

# A camera that fails this many reads in a row has stalled; the generator raises
# instead of spinning forever, so the loop can pause on the alert.
_MAX_CONSECUTIVE_READ_FAILURES = 100

# Some platform timers are coarse (Windows is ~15 ms), so two frames read back
# to back can share a tick. Frames must stay strictly ordered, so a shared tick
# is nudged forward by this much; the base timestamp is still time.monotonic().
_TS_EPSILON_S = 1e-6


class CameraError(RuntimeError):
    """A frame source could not be opened or read."""


def _wall_iso() -> str:
    return datetime.now(UTC).isoformat()


def _next_ts(previous: float) -> float:
    """Return a timestamp strictly greater than ``previous``."""

    now = time.monotonic()
    if now <= previous:
        return previous + _TS_EPSILON_S
    return now


def _replay(spec: str) -> Iterator[Frame]:
    path_part, _, fps_part = spec.partition("@")

    fps: float | None = None
    if fps_part:
        try:
            fps = float(fps_part)
        except ValueError as exc:
            raise CameraError(
                f"replay fps is not a number: {fps_part!r}"
            ) from exc
        if fps <= 0:
            raise CameraError(f"replay fps must be > 0: {fps}")

    directory = Path(path_part)
    if not directory.is_dir():
        raise CameraError(f"replay directory not found: {directory}")

    paths = sorted(
        (
            path
            for path in directory.iterdir()
            if path.is_file() and path.suffix.lower() in _IMAGE_SUFFIXES
        ),
        key=lambda path: path.name,
    )

    interval = (1.0 / fps) if fps is not None else None
    start = time.monotonic()
    frame_id = 0
    last_ts = 0.0

    for index, path in enumerate(paths):
        if interval is not None:
            delay = (start + index * interval) - time.monotonic()
            if delay > 0:
                time.sleep(delay)

        image = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if image is None:
            continue

        last_ts = _next_ts(last_ts)
        yield Frame(
            frame_id=frame_id,
            ts=last_ts,
            wall_iso=_wall_iso(),
            image=image,
        )
        frame_id += 1


def _camera(spec: str, width: int, height: int) -> Iterator[Frame]:
    try:
        index = int(spec)
    except ValueError as exc:
        raise CameraError(
            f"camera source must be an index or replay:<dir>: {spec!r}"
        ) from exc

    capture = cv2.VideoCapture(index)
    if not capture.isOpened():
        capture.release()
        raise CameraError(f"camera {index} could not be opened")

    capture.set(cv2.CAP_PROP_FRAME_WIDTH, float(width))
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, float(height))

    frame_id = 0
    failures = 0
    last_ts = 0.0

    try:
        while True:
            ok, image = capture.read()
            if not ok or image is None or image.size == 0:
                failures += 1
                if failures >= _MAX_CONSECUTIVE_READ_FAILURES:
                    raise CameraError(f"camera {index} stopped delivering frames")
                continue

            failures = 0
            last_ts = _next_ts(last_ts)
            yield Frame(
                frame_id=frame_id,
                ts=last_ts,
                wall_iso=_wall_iso(),
                image=image,
            )
            frame_id += 1
    finally:
        capture.release()


def open_source(spec: str, width: int, height: int) -> Iterator[Frame]:
    """Open a frame source.

    ``"<int>"`` opens ``cv2.VideoCapture(index)`` with the resolution set and
    skips frames whose read fails. ``"replay:<dir>"`` replays the images in
    ``<dir>`` sorted by filename; ``"replay:<dir>@<fps>"`` paces playback to
    ``<fps>`` (default: as fast as possible).
    """

    text = str(spec)

    if text.startswith(_REPLAY_PREFIX):
        return _replay(text[len(_REPLAY_PREFIX):])

    return _camera(text, width, height)


__all__ = ["CameraError", "open_source"]
