"""Nozzle-ROI crops from data/images.csv → data/crops/<trial>/<image>.jpg + data/crops.csv (T-0009, 08 P8).

    python scripts/build_crops.py --images data/images.csv --root D:/caxton --out data/crops [--size 320] [--px 224]
        [--workers 4]

Resumable: an existing crop is not rewritten. Missing or unreadable images are counted and listed in
<out>/../crops_missing.txt; they never stop the run.
"""
import argparse
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cv2
import pandas as pd

CROPS_COLS = ["crop_path", "image_path", "trial_id", "geometry", "ts_s", "cause", "flow_cls", "speed_cls", "z_cls",
              "nozzle_cls", "flow_pct", "speed_pct", "nozzle_target_c"]


def box(x: float, y: float, w: int, h: int, size: int = 320) -> tuple[int, int, int, int]:
    """size×size box centred on (x, y), shifted to stay inside a w×h frame: (x1, y1, x2, y2)."""
    x1 = min(max(round(x) - size // 2, 0), max(w - size, 0))
    y1 = min(max(round(y) - size // 2, 0), max(h - size, 0))
    return x1, y1, min(x1 + size, w), min(y1 + size, h)


def crop_one(src: Path, dst: Path, x: float, y: float, size: int, px: int) -> str:
    """'skipped' | 'written' | 'missing'. cv2 releases the GIL, so threads are enough."""
    if dst.exists():
        return "skipped"
    img = cv2.imread(str(src))
    if img is None:
        return "missing"
    x1, y1, x2, y2 = box(x, y, img.shape[1], img.shape[0], size)
    crop = cv2.resize(img[y1:y2, x1:x2], (px, px), interpolation=cv2.INTER_AREA)
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(".tmp.jpg")  # a killed run never leaves a half-written crop that resume would skip
    cv2.imwrite(str(tmp), crop, [cv2.IMWRITE_JPEG_QUALITY, 95])
    tmp.replace(dst)
    return "written"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", default="data/images.csv")
    ap.add_argument("--root", required=True, help="the folder holding caxton_dataset/ (read-only)")
    ap.add_argument("--out", default="data/crops")
    ap.add_argument("--size", type=int, default=320, help="ROI side in frame pixels")
    ap.add_argument("--px", type=int, default=224, help="crop side after resizing")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args(argv)
    out, root = Path(a.out), Path(a.root)
    images = pd.read_csv(a.images)
    dsts = [out / t / (Path(p).stem + ".jpg") for t, p in zip(images.trial_id, images.image_path)]
    with ThreadPoolExecutor(a.workers) as ex:
        status = list(ex.map(crop_one, (root / p for p in images.image_path), dsts, images.nozzle_x,
                             images.nozzle_y, [a.size] * len(images), [a.px] * len(images)))

    ok = [s != "missing" for s in status]
    crops = images[ok].assign(crop_path=[d.as_posix() for d, k in zip(dsts, ok) if k])[CROPS_COLS]
    crops.to_csv(out.parent / "crops.csv", index=False)
    missing = images.image_path[[not k for k in ok]]
    (out.parent / "crops_missing.txt").write_text("".join(p + "\n" for p in missing), encoding="utf-8")
    for s in ("written", "skipped", "missing"):
        print(f"{s}: {status.count(s)}")
    print(f"wrote {out.parent / 'crops.csv'} ({len(crops)} rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
