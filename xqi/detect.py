import re

from xqi.types import DEFECTS, Detection, Frame

# Normalised model class names that are not in DEFECTS verbatim.
ALIASES = {
    "over_extr": "over_extrusion",
    "under_extr": "under_extrusion",
}
NO_DEFECT = {"no_defect", "none", "normal", "good"}


def normalise(name: str) -> str | None:
    """Map a model class name to a DEFECTS entry, or None for no-defect."""
    key = re.sub(r"[\s\-]+", "_", name.strip().lower()).strip("._")
    key = ALIASES.get(key, key)
    if key in NO_DEFECT:
        return None
    if key not in DEFECTS:
        raise ValueError(f"Unknown detector class: {name!r}")
    return key


class Detector:
    def __init__(self, weights, imgsz, conf, device, model=None):
        if model is None:
            from ultralytics import YOLO

            model = YOLO(weights)
        self.model = model
        self.imgsz = imgsz
        self.conf = conf
        self.device = device
        self.classes = {
            int(i): normalise(name) for i, name in model.names.items()
        }

    def __call__(self, frame: Frame) -> list[Detection]:
        boxes = self.model(
            frame.image,
            imgsz=self.imgsz,
            conf=self.conf,
            device=self.device,
            verbose=False,
        )[0].boxes
        h, w = frame.image.shape[:2]
        dets = []
        for xyxy, conf, cls in zip(
            boxes.xyxy.tolist(), boxes.conf.tolist(), boxes.cls.tolist()
        ):
            name = self.classes[int(cls)]
            if name is None or conf < self.conf:
                continue
            x1, y1, x2, y2 = xyxy
            dets.append(
                Detection(
                    frame_id=frame.frame_id,
                    cls=name,
                    conf=float(conf),
                    xyxy=(x1, y1, x2, y2),
                    area_frac=(x2 - x1) * (y2 - y1) / (w * h),
                )
            )
        return dets
