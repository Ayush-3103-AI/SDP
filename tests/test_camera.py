import cv2
import numpy as np
import pytest

from xqi.camera import open_source
from xqi.config import load
from xqi.printer import FakePrinter
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


def _write_crops_csv(tmp_path):
    """3 prints, rows shuffled; each crop's pixel value is its row number × 10 so order is visible."""
    rows = [  # trial, ts_s, flow, speed, nozzle_target
        ("p1", 0.10, 62, 100, 210), ("p0", 0.00, 100, 100, 210), ("p2", 0.00, 90, 80, 230),
        ("p1", 0.00, 100, 100, 210), ("p1", 0.05, 72, 120, 195), ("p0", 0.05, 30, 100, 210),
    ]
    lines = ["crop_path,trial_id,ts_s,flow_pct,speed_pct,nozzle_target_c"]
    for i, (trial, ts, flow, speed, nozzle) in enumerate(rows):
        path = tmp_path / f"{i}.png"
        assert cv2.imwrite(str(path), np.full((4, 4, 3), i * 10, dtype=np.uint8))
        lines.append(f"{path.as_posix()},{trial},{ts},{flow},{speed},{nozzle}")
    csv = tmp_path / "crops.csv"
    csv.write_text("\n".join(lines) + "\n")
    return csv


def test_caxton_source_order_and_seeding(tmp_path):
    csv = _write_crops_csv(tmp_path)
    printer = FakePrinter()
    seen = []
    for frame in open_source(f"caxton:{csv}#p1", 0, 0, printer=printer):
        s = printer.get_state()
        seen.append((int(frame.image[0, 0, 0]), frame.ts, s.flow_pct, s.speed_pct, s.nozzle_target_c))

    assert [(v, f, sp, n) for v, _, f, sp, n in seen] == [
        (30, 100, 100, 210), (40, 72, 120, 195), (0, 62, 100, 210)]  # p1's rows in ts_s order
    ts = [t for _, t, *_ in seen]
    # Logged deltas, less a ~15.6 ms Windows monotonic tick and some scheduler jitter.
    assert ts[1] - ts[0] >= 0.05 - 0.03 and ts[2] - ts[1] >= 0.05 - 0.03
    # Seeding is a disturbance, not a command: nothing sent, no cooldown started.
    assert printer.sent == []
    assert all(t == float("-inf") for t in printer.get_state().last_change_ts.values())


def test_caxton_source_fps_and_unknown_trial(tmp_path):
    csv = _write_crops_csv(tmp_path)
    frames = list(open_source(f"caxton:{csv}#p0@10", 0, 0, printer=FakePrinter()))
    assert len(frames) == 2 and frames[1].ts - frames[0].ts >= 0.1 - 0.03

    with pytest.raises(ValueError):
        next(open_source(f"caxton:{csv}#p9", 0, 0, printer=FakePrinter()))


def test_caxton_demo_config_loads():
    cfg = load("config/caxton_demo.yaml")
    assert cfg.printer.kind == "fake" and cfg.camera.source.startswith("caxton:")
    assert cfg.detector.weights is None and cfg.proactive.enabled and cfg.mode == "advisory"


@pytest.mark.hw
def test_camera_yields_frames():
    source = open_source("0", 1920, 1056)
    frames = [next(source) for _ in range(3)]

    assert [frame.frame_id for frame in frames] == [0, 1, 2]
    assert frames[0].image.ndim == 3
    assert frames[0].ts < frames[1].ts < frames[2].ts
