import cv2
import pandas as pd
from caxton_fixture import adapt, load_script

build_crops = load_script("build_crops")

CROPS_COLS = ["crop_path", "image_path", "trial_id", "geometry", "ts_s", "cause", "flow_cls", "speed_cls", "z_cls",
              "nozzle_cls", "flow_pct", "speed_pct", "nozzle_target_c"]


def _run(tmp_path, data):
    return build_crops.main(["--images", str(data / "images.csv"), "--root", str(tmp_path / "raw"),
                             "--out", str(data / "crops"), "--workers", "2"])


def test_box_stays_inside_the_frame():
    assert build_crops.box(640, 360, 1280, 720) == (480, 200, 800, 520)
    assert build_crops.box(10, 715, 1280, 720) == (0, 400, 320, 720)
    assert build_crops.box(1279, 0, 1280, 720) == (960, 0, 1280, 320)


def test_crops_are_224_and_listed(tmp_path, capsys):
    data = adapt(tmp_path)
    assert _run(tmp_path, data) == 0
    crops, images = pd.read_csv(data / "crops.csv"), pd.read_csv(data / "images.csv")
    assert list(crops.columns) == CROPS_COLS
    assert crops.image_path.tolist() == images.image_path.tolist()  # multi rows included
    assert (crops.cause == "multi").sum() == 2
    for p in crops.crop_path:
        assert cv2.imread(p).shape == (224, 224, 3)
    corner = cv2.imread(crops.crop_path[crops.image_path == "caxton_dataset/print1/image-0.jpg"].item())
    assert corner[-5, 5].mean() > 200 and corner[5, -5].mean() < 100  # the corner nozzle sits bottom-left
    assert "written: 35" in capsys.readouterr().out


def test_missing_image_counted_and_rerun_writes_nothing(tmp_path, capsys):
    data = adapt(tmp_path)
    (tmp_path / "raw" / "caxton_dataset" / "print2" / "image-3.jpg").unlink()
    assert _run(tmp_path, data) == 0
    assert "missing: 1" in capsys.readouterr().out
    assert (data / "crops_missing.txt").read_text().split() == ["caxton_dataset/print2/image-3.jpg"]
    crops = pd.read_csv(data / "crops.csv")
    assert len(crops) == 34 and "caxton_dataset/print2/image-3.jpg" not in set(crops.image_path)

    mtimes = {p: (data / "crops").joinpath(p).stat().st_mtime_ns for p in ["p0/image-0.jpg", "p2/image-9.jpg"]}
    assert _run(tmp_path, data) == 0
    out = capsys.readouterr().out
    assert "written: 0" in out and "skipped: 34" in out
    assert mtimes == {p: (data / "crops").joinpath(p).stat().st_mtime_ns for p in mtimes}
