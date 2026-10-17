"""T-0029 — the frame sources (replay folder; the camera is an ``hw`` test)."""

from __future__ import annotations

import itertools
from pathlib import Path

import cv2
import numpy as np
import pytest

from xqi.camera import CameraError, open_source


def write_image(path: Path, value: int = 40) -> None:
    image = np.full((6, 8, 3), value, dtype=np.uint8)
    assert cv2.imwrite(str(path), image)


def write_spec(tmp_path: Path, names: list[str]) -> str:
    for index, name in enumerate(names):
        write_image(tmp_path / name, value=10 * (index + 1))
    return f"replay:{tmp_path}"


def test_replay_yields_frames_in_name_order(tmp_path):
    spec = write_spec(tmp_path, ["a.png", "b.png", "c.png"])

    frames = list(open_source(spec, 8, 6))

    assert [frame.frame_id for frame in frames] == [0, 1, 2]
    assert [int(frame.image.mean()) for frame in frames] == [10, 20, 30]


def test_replay_timestamps_increase(tmp_path):
    spec = write_spec(tmp_path, ["a.png", "b.png", "c.png"])

    frames = list(open_source(spec, 8, 6))

    times = [frame.ts for frame in frames]
    assert all(later > earlier for earlier, later in itertools.pairwise(times))


def test_replay_is_sorted_by_filename_not_number(tmp_path):
    spec = write_spec(tmp_path, ["1.png", "2.png", "10.png"])

    frames = list(open_source(spec, 8, 6))

    # "10.png" sorts before "2.png" lexicographically.
    assert [int(frame.image.mean()) for frame in frames] == [10, 30, 20]


def test_replay_ends_with_stop_iteration(tmp_path):
    spec = write_spec(tmp_path, ["a.png"])

    generator = open_source(spec, 8, 6)
    next(generator)

    with pytest.raises(StopIteration):
        next(generator)


def test_replay_skips_unreadable_images(tmp_path):
    write_image(tmp_path / "a.png")
    (tmp_path / "b.png").write_bytes(b"not an image")
    write_image(tmp_path / "c.png")

    frames = list(open_source(f"replay:{tmp_path}", 8, 6))

    assert [frame.frame_id for frame in frames] == [0, 1]


def test_empty_replay_directory_yields_nothing(tmp_path):
    assert list(open_source(f"replay:{tmp_path}", 8, 6)) == []


def test_missing_replay_directory_raises(tmp_path):
    missing = tmp_path / "nope"

    with pytest.raises(CameraError):
        list(open_source(f"replay:{missing}", 8, 6))


def test_replay_keeps_the_file_resolution(tmp_path):
    spec = write_spec(tmp_path, ["a.png"])

    frame = next(open_source(spec, 1920, 1056))

    assert frame.image.shape == (6, 8, 3)
    assert frame.image.dtype == np.uint8


def test_replay_is_deterministic(tmp_path):
    spec = write_spec(tmp_path, ["a.png", "b.png", "c.png"])

    first = [int(frame.image.mean()) for frame in open_source(spec, 8, 6)]
    second = [int(frame.image.mean()) for frame in open_source(spec, 8, 6)]

    assert first == second


def test_replay_fps_is_accepted(tmp_path):
    spec = write_spec(tmp_path, ["a.png", "b.png", "c.png"])

    frames = list(open_source(f"{spec}@1000", 8, 6))

    assert len(frames) == 3


def test_replay_bad_fps_raises(tmp_path):
    spec = write_spec(tmp_path, ["a.png"])

    with pytest.raises(CameraError):
        list(open_source(f"{spec}@nope", 8, 6))

    with pytest.raises(CameraError):
        list(open_source(f"{spec}@0", 8, 6))


def test_closing_a_replay_generator_is_clean(tmp_path):
    spec = write_spec(tmp_path, ["a.png", "b.png"])

    generator = open_source(spec, 8, 6)
    next(generator)
    generator.close()


def test_bad_camera_spec_raises_without_hardware():
    with pytest.raises(CameraError):
        list(open_source("not-an-index", 640, 480))


@pytest.mark.hw
def test_live_camera_reads_a_frame():
    """Needs a real webcam; runs only with -m hw (T-0029)."""

    frame = next(open_source("0", 1920, 1056))

    assert frame.image.ndim == 3
    assert frame.frame_id == 0
