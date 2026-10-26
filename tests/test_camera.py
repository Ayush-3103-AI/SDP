import cv2
import numpy as np
import pytest

from xqi.camera import open_source
from xqi.types import Frame


def _write_pngs(folder, names):
    for value, name in enumerate(names):
        image = np.full((4, 6, 3), value * 40, dtype=np.uint8)
        assert cv2.imwrite(str(folder / name), image)


def test_replay_yields_frames_in_name_order_then_stops(tmp_path):
    _write_pngs(tmp_path, ["b.png", "a.png", "c.png"])
    (tmp_path / "notes.txt").write_text("not an image")

    source = open_source(f"replay:{tmp_path}", 1920, 1056)
    frames = [next(source) for _ in range(3)]
    with pytest.raises(StopIteration):
        next(source)

    assert all(isinstance(frame, Frame) for frame in frames)
    assert [frame.frame_id for frame in frames] == [0, 1, 2]
    # b.png was written first (value 0), a.png second (40), c.png third (80).
    assert [int(frame.image[0, 0, 0]) for frame in frames] == [40, 0, 80]
    assert frames[0].image.shape == (4, 6, 3)
    assert frames[0].image.dtype == np.uint8
    assert frames[0].ts < frames[1].ts < frames[2].ts
    assert all(frame.wall_iso for frame in frames)


def test_replay_fps_paces_playback(tmp_path):
    _write_pngs(tmp_path, ["0.png", "1.png", "2.png"])

    frames = list(open_source(f"replay:{tmp_path}@10", 0, 0))

    assert len(frames) == 3
    # 2 intervals at 10 fps, less one ~15.6 ms Windows monotonic tick.
    assert frames[2].ts - frames[0].ts >= 0.2 - 0.02


def test_unknown_spec_raises():
    with pytest.raises(ValueError):
        next(open_source("rtsp://nope", 1920, 1056))


@pytest.mark.hw
def test_camera_yields_frames():
    source = open_source("0", 1920, 1056)
    frames = [next(source) for _ in range(3)]

    assert [frame.frame_id for frame in frames] == [0, 1, 2]
    assert frames[0].image.ndim == 3
    assert frames[0].ts < frames[1].ts < frames[2].ts
