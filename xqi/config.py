from dataclasses import dataclass
from pathlib import Path
from typing import Any, get_args

import yaml

from xqi.types import DEFECTS, Var


class ConfigError(ValueError):
    """Raised when the configuration violates the project contract."""


@dataclass(frozen=True, slots=True)
class PrinterConfig:
    kind: str
    url: str
    api_key_env: str
    timeout_s: float
    poll_s: float
    nominal: dict[str, float]


@dataclass(frozen=True, slots=True)
class CameraConfig:
    source: str
    width: int
    height: int
    max_gap_s: float


@dataclass(frozen=True, slots=True)
class DetectorConfig:
    weights: str
    imgsz: int
    conf: float
    device: str


@dataclass(frozen=True, slots=True)
class ConfirmConfig:
    hits: dict[str, int]
    rearm_frames: int


@dataclass(frozen=True, slots=True)
class CriticalConfig:
    clog: str
    layer_shift: str
    spaghetti: str


@dataclass(frozen=True, slots=True)
class SeverityConfig:
    a_ref: float
    h_ref: float
    window: float


@dataclass(frozen=True, slots=True)
class CauseModelConfig:
    weights: str
    crop_pad: float
    input_px: int
    device: str


@dataclass(frozen=True, slots=True)
class ConformalConfig:
    alpha: float
    qhat_file: str


@dataclass(frozen=True, slots=True)
class CorrectionConfig:
    d_min: dict[str, float]
    d_max: dict[str, float]


@dataclass(frozen=True, slots=True)
class L1Config:
    nozzle_temp: tuple[float, float]
    bed_temp: tuple[float, float]
    flow: tuple[float, float]
    speed: tuple[float, float]


@dataclass(frozen=True, slots=True)
class L2Config:
    step: dict[str, float]
    cooldown_s: dict[str, float]


@dataclass(frozen=True, slots=True)
class L3Config:
    material: str
    window: dict[str, tuple[float, float]]


@dataclass(frozen=True, slots=True)
class L4Config:
    tau: float


@dataclass(frozen=True, slots=True)
class EnvelopeConfig:
    L1: L1Config
    L2: L2Config
    L3: L3Config
    L4: L4Config


@dataclass(frozen=True, slots=True)
class SensorsConfig:
    temp_dev_c: float
    temp_dev_s: float
    settle_s: dict[str, float]


@dataclass(frozen=True, slots=True)
class HitlConfig:
    timeout_s: float
    timeout_action: str


@dataclass(frozen=True, slots=True)
class VerifyConfig:
    window_s: float
    settle_s: float


@dataclass(frozen=True, slots=True)
class AttributionConfig:
    enabled: bool
    layer: str


@dataclass(frozen=True, slots=True)
class Config:
    mode: str
    run_dir: str
    printer: PrinterConfig
    camera: CameraConfig
    detector: DetectorConfig
    confirm: ConfirmConfig
    critical: CriticalConfig
    severity: SeverityConfig
    causes_file: str
    cause_model: CauseModelConfig
    conformal: ConformalConfig
    correction: CorrectionConfig
    envelope: EnvelopeConfig
    sensors: SensorsConfig
    hitl: HitlConfig
    verify: VerifyConfig
    attribution: AttributionConfig


@dataclass(frozen=True, slots=True)
class Causes:
    """Runtime cause taxonomy from config/causes.yaml (types.py holds the defaults)."""

    causes: tuple[str, ...]
    cause_action: dict[str, tuple[str, int] | None]
    cause_defects: dict[str, tuple[str, ...]]
    deck_recipes: dict[str, dict[str, float]]


def _require(data: dict[str, Any], key: str) -> Any:
    if key not in data:
        raise ConfigError(f"{key}: missing")
    return data[key]


def _float_pair(value: Any, key: str) -> tuple[float, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ConfigError(f"{key}: expected [min, max]")
    return float(value[0]), float(value[1])


def _var_map(
    value: dict[str, Any],
    key: str,
    *,
    cast=float,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConfigError(f"{key}: expected mapping")

    expected = {"nozzle_temp", "bed_temp", "flow", "speed"}
    missing = expected - set(value)
    if missing:
        missing_key = min(missing)
        raise ConfigError(f"{key}.{missing_key}: missing")

    return {name: cast(value[name]) for name in expected}


def _build_config(data: dict[str, Any]) -> Config:
    mode = _require(data, "mode")
    if mode not in {"baseline", "gated-recipe", "auto", "advisory"}:
        raise ConfigError("mode: must be baseline, gated-recipe, auto, or advisory")

    printer_data = _require(data, "printer")
    nominal = _var_map(printer_data.get("nominal", {}), "printer.nominal")

    printer = PrinterConfig(
        kind=printer_data["kind"],
        url=printer_data["url"],
        api_key_env=printer_data["api_key_env"],
        timeout_s=float(printer_data["timeout_s"]),
        poll_s=float(printer_data["poll_s"]),
        nominal=nominal,
    )

    camera_data = _require(data, "camera")
    camera = CameraConfig(
        source=str(camera_data["source"]),
        width=int(camera_data["width"]),
        height=int(camera_data["height"]),
        max_gap_s=float(camera_data["max_gap_s"]),
    )

    detector_data = _require(data, "detector")
    detector = DetectorConfig(
        weights=str(detector_data["weights"]),
        imgsz=int(detector_data["imgsz"]),
        conf=float(detector_data["conf"]),
        device=str(detector_data["device"]),
    )

    confirm_data = _require(data, "confirm")
    hits_raw = confirm_data["hits"]
    hits = {str(k): int(v) for k, v in hits_raw.items()}

    for defect in (
        "clog",
        "layer_shift",
        "spaghetti",
        "over_extrusion",
        "under_extrusion",
        "stringing",
        "warping",
    ):
        if defect not in hits:
            raise ConfigError(f"confirm.hits.{defect}: missing")
        if hits[defect] < 1:
            raise ConfigError(f"confirm.hits.{defect}: must be >= 1")

    confirm = ConfirmConfig(
        hits=hits,
        rearm_frames=int(confirm_data["rearm_frames"]),
    )

    critical_data = _require(data, "critical")

    for defect in ("clog", "layer_shift", "spaghetti"):
        action = critical_data.get(defect)
        if action not in {"estop", "pause"}:
            raise ConfigError(
                f"critical.{defect}: must be estop or pause"
            )

    critical = CriticalConfig(
        clog=critical_data["clog"],
        layer_shift=critical_data["layer_shift"],
        spaghetti=critical_data["spaghetti"],
    )

    severity_data = _require(data, "severity")
    severity = SeverityConfig(
        a_ref=float(severity_data["a_ref"]),
        h_ref=float(severity_data["h_ref"]),
        window=float(severity_data["window"]),
    )

    cause_model_data = _require(data, "cause_model")
    cause_model = CauseModelConfig(
        weights=str(cause_model_data["weights"]),
        crop_pad=float(cause_model_data["crop_pad"]),
        input_px=int(cause_model_data["input_px"]),
        device=str(cause_model_data["device"]),
    )

    conformal_data = _require(data, "conformal")
    conformal = ConformalConfig(
        alpha=float(conformal_data["alpha"]),
        qhat_file=str(conformal_data["qhat_file"]),
    )

    correction_data = _require(data, "correction")
    d_min = _var_map(correction_data["d_min"], "correction.d_min")
    d_max = _var_map(correction_data["d_max"], "correction.d_max")

    envelope_data = _require(data, "envelope")

    l1_data = _require(envelope_data, "L1")
    l1 = L1Config(
        nozzle_temp=_float_pair(
            l1_data["nozzle_temp"],
            "envelope.L1.nozzle_temp",
        ),
        bed_temp=_float_pair(
            l1_data["bed_temp"],
            "envelope.L1.bed_temp",
        ),
        flow=_float_pair(
            l1_data["flow"],
            "envelope.L1.flow",
        ),
        speed=_float_pair(
            l1_data["speed"],
            "envelope.L1.speed",
        ),
    )

    l2_data = _require(envelope_data, "L2")
    step = _var_map(l2_data["step"], "envelope.L2.step")
    cooldown_s = _var_map(
        l2_data["cooldown_s"],
        "envelope.L2.cooldown_s",
    )

    for var in step:
        if d_max[var] > step[var]:
            raise ConfigError(
                f"correction.d_max.{var}: must be <= envelope.L2.step.{var}"
            )

    l2 = L2Config(
        step=step,
        cooldown_s=cooldown_s,
    )

    l3_data = _require(envelope_data, "L3")
    l3_window_raw = l3_data["window"]
    l3_window = {
        var: _float_pair(
            l3_window_raw[var],
            f"envelope.L3.window.{var}",
        )
        for var in ("nozzle_temp", "bed_temp", "flow", "speed")
    }

    for var, (low, high) in l3_window.items():
        l1_low, l1_high = getattr(l1, var)

        if low < l1_low or high > l1_high:
            raise ConfigError(
                f"envelope.L3.window.{var}: must be within envelope.L1.{var}"
            )

    l3 = L3Config(
        material=str(l3_data["material"]),
        window=l3_window,
    )

    l4_data = _require(envelope_data, "L4")
    l4 = L4Config(tau=float(l4_data["tau"]))

    envelope = EnvelopeConfig(
        L1=l1,
        L2=l2,
        L3=l3,
        L4=l4,
    )

    sensors_data = _require(data, "sensors")
    sensors = SensorsConfig(
        temp_dev_c=float(sensors_data["temp_dev_c"]),
        temp_dev_s=float(sensors_data["temp_dev_s"]),
        settle_s={
            str(k): float(v)
            for k, v in sensors_data["settle_s"].items()
        },
    )

    hitl_data = _require(data, "hitl")
    if hitl_data["timeout_action"] not in {"noop", "pause"}:
        raise ConfigError(
            "hitl.timeout_action: must be noop or pause"
        )

    hitl = HitlConfig(
        timeout_s=float(hitl_data["timeout_s"]),
        timeout_action=str(hitl_data["timeout_action"]),
    )

    verify_data = _require(data, "verify")
    verify = VerifyConfig(
        window_s=float(verify_data["window_s"]),
        settle_s=float(verify_data["settle_s"]),
    )

    attribution_data = _require(data, "attribution")
    attribution = AttributionConfig(
        enabled=bool(attribution_data["enabled"]),
        layer=str(attribution_data["layer"]),
    )

    return Config(
        mode=mode,
        run_dir=str(data["run_dir"]),
        printer=printer,
        camera=camera,
        detector=detector,
        confirm=confirm,
        critical=critical,
        severity=severity,
        causes_file=str(data["causes_file"]),
        cause_model=cause_model,
        conformal=conformal,
        correction=CorrectionConfig(
            d_min=d_min,
            d_max=d_max,
        ),
        envelope=envelope,
        sensors=sensors,
        hitl=hitl,
        verify=verify,
        attribution=attribution,
    )


def _build_causes(data: dict[str, Any]) -> Causes:
    causes = tuple(str(c) for c in _require(data, "causes"))
    known = set(causes)

    cause_action = {}
    for cause, action in _require(data, "cause_action").items():
        key = f"cause_action.{cause}"
        if cause not in known:
            raise ConfigError(f"{key}: not in causes")
        if action is None:
            cause_action[cause] = None
            continue
        if (
            not isinstance(action, list)
            or len(action) != 2
            or action[0] not in get_args(Var)
            or action[1] not in (-1, 1)
        ):
            raise ConfigError(f"{key}: expected [<var>, -1 | 1] or null")
        cause_action[cause] = (action[0], action[1])

    missing = known - set(cause_action)
    if missing:
        raise ConfigError(f"cause_action.{min(missing)}: missing")

    cause_defects = {}
    for cause, defects in _require(data, "cause_defects").items():
        key = f"cause_defects.{cause}"
        if cause not in known:
            raise ConfigError(f"{key}: not in causes")
        unknown = set(defects) - set(DEFECTS)
        if unknown:
            raise ConfigError(f"{key}: unknown defect {min(unknown)}")
        cause_defects[cause] = tuple(defects)

    deck_recipes = {}
    for defect, recipe in _require(data, "deck_recipes").items():
        if defect not in DEFECTS:
            raise ConfigError(f"deck_recipes.{defect}: unknown defect")
        bad = set(recipe) - set(get_args(Var))
        if bad:
            raise ConfigError(f"deck_recipes.{defect}.{min(bad)}: unknown var")
        deck_recipes[defect] = dict(recipe)

    return Causes(
        causes=causes,
        cause_action=cause_action,
        cause_defects=cause_defects,
        deck_recipes=deck_recipes,
    )


def _read_yaml(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)

    if not config_path.exists():
        raise ConfigError(f"{config_path}: file not found")

    try:
        with config_path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
    except yaml.YAMLError as exc:
        raise ConfigError(f"{config_path}: invalid YAML") from exc

    if not isinstance(data, dict):
        raise ConfigError(f"{config_path}: top level must be a mapping")

    return data


def load(path: str | Path) -> Config:
    """Load and validate a YAML configuration file."""

    return _build_config(_read_yaml(path))


def load_causes(path: str | Path) -> Causes:
    """Load and validate config/causes.yaml (pass Config.causes_file)."""

    return _build_causes(_read_yaml(path))


__all__ = [
    "Causes",
    "Config",
    "ConfigError",
    "load",
    "load_causes",
]