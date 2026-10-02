<!-- HEAD
FILE:     09-interfaces.md
PHASE:    2 — SPECIFY
UPDATED:  2026-10-03
STATUS:   draft (awaiting gate)
SUMMARY:  Frozen contracts:
          §Types: dataclasses in xqi/types.py, units in field names.
          §Constants: DEFECTS (7), CAUSES (9, provisional until T-0007), CAUSE_ACTION map.
          §Config: full default.yaml key list. §Data: canonical trials.csv / images.csv /
          crops.csv / splits/*.json. §Store: 9 SQLite tables with single-writer ownership.
          §Module APIs: one signature per module. §CLI: `python -m xqi <cmd>`.
          SCHEMA_VERSION = 1; any breaking change bumps it and is a DESCEND to Phase 2.
OPEN:     CAUSES and CAUSE_DEFECTS are finalised in T-0007 (edit config/causes.yaml, not code).
-->

# Interfaces

## Repo layout (target)
```
SDP/
  CLAUDE.md  pyproject.toml  .gitignore
  config/default.yaml  config/causes.yaml
  xqi/  __init__.py __main__.py types.py config.py store.py printer.py camera.py detect.py
        gate.py orchestrator.py verify.py ui.py ui_data.py study.py
        explain/ __init__.py cause_model.py conformal.py counterfactual.py attribution.py sensors.py
  scripts/  adapt_trials.py audit_data.py make_splits.py build_crops.py eval_detector.py eval_cause.py train_cause.py
            eval_conformal.py eval_counterfactual.py derive_window.py gate_audit.py octoprint_smoke.py
            make_campaign.py eval_runs.py eval_latency.py analyze_study.py acceptance.py
  tests/    test_*.py   (markers: gpu, hw, slow)
  data/     (gitignored) raw/ trials.csv images.csv crops/ crops.csv splits/ (splits/ IS committed)
  models/   (gitignored) yolo/best.pt cause/*.pt cause/qhat.json
  runs/     (gitignored) <run_id>/events.sqlite heatmaps/ frames/
  reports/  *.md (committed)
  docs/     experiment_protocol.md study_protocol.md
  project-context/
```

## §Types (`xqi/types.py`, `@dataclass(frozen=True, slots=True)` unless noted)
```python
SCHEMA_VERSION = 1
Var = Literal["nozzle_temp", "bed_temp", "flow", "speed"]

Frame(frame_id: int, ts: float, wall_iso: str, image: np.ndarray)          # BGR uint8 HxWx3; ts = time.monotonic()
Detection(frame_id: int, cls: str, conf: float, xyxy: tuple[float,float,float,float], area_frac: float)
ConfirmedDefect(defect_id: str, cls: str, frame_id: int, t0: float, t_conf: float,
                conf: float, xyxy: tuple[float,...], area_frac: float, recent_hits: int,
                severity: float, critical: bool)
PrinterState(ts: float, state: str, nozzle_actual_c: float, nozzle_target_c: float,
             bed_actual_c: float, bed_target_c: float, flow_pct: float, speed_pct: float,
             progress_pct: float | None, last_change_ts: dict[Var, float])
    .setpoint(v) -> float     # nozzle_target_c | bed_target_c | flow_pct | speed_pct
CauseEstimate(probs: dict[str, float], top: str, p_top: float)
CauseSet(members: tuple[str, ...], alpha: float, qhat: float)
Proposal(proposal_id: str, defect_id: str, cause: str, var: Var, from_value: float,
         delta: float, to_value: float, gcode: tuple[str, ...], counterfactual: str)
LayerResult(layer: Literal["L1","L2","L3","L4"], passed: bool, reason: str)
GateDecision(proposal_id: str, passed: bool, clipped: bool, final_delta: float,
             final_value: float, final_gcode: tuple[str, ...], layers: tuple[LayerResult, ...])
EventVerdict(defect_id: str, verdict: Literal["CRITICAL","APPLY_RAW","APPLY","PROPOSE","ESCALATE","NOOP"],
             reason: str, proposal_ids: tuple[str, ...])
OperatorDecision(proposal_id: str | None, defect_id: str,
                 choice: Literal["apply","modify","reject","pause","stop","timeout"],
                 modified_delta: float | None, operator: str, wall_iso: str, latency_s: float)
Outcome(action_id: str, defect_id: str, cls: str, verdict: Literal["resolved","persisted","worsened","unknown"],
        r_before: float, r_after: float, window_s: float)
```
Every dataclass has `to_dict()` / `from_dict()` that round-trip through JSON (numpy arrays excluded; `Frame.image` is never serialised).

## §Constants
```python
DEFECTS = ("clog","layer_shift","over_extrusion","spaghetti","stringing","under_extrusion","warping")
# Provisional; loaded from config/causes.yaml, frozen by T-0007:
CAUSES = ("none","nozzle_temp_low","nozzle_temp_high","flow_low","flow_high",
          "speed_low","speed_high","bed_temp_low","misalignment")
CAUSE_ACTION = {  # cause -> (var, d) with d=-1 low / +1 high; None = not a setpoint fix
  "nozzle_temp_low":("nozzle_temp",-1), "nozzle_temp_high":("nozzle_temp",+1),
  "flow_low":("flow",-1), "flow_high":("flow",+1), "speed_low":("speed",-1), "speed_high":("speed",+1),
  "bed_temp_low":("bed_temp",-1), "none":None, "misalignment":None }
CAUSE_DEFECTS = {  # [assumed] physics prior; used for label assignment + audit
  "nozzle_temp_high":["stringing","over_extrusion"], "nozzle_temp_low":["under_extrusion","clog"],
  "flow_high":["over_extrusion"], "flow_low":["under_extrusion"],
  "speed_high":["under_extrusion"], "speed_low":["over_extrusion","stringing"],
  "bed_temp_low":["warping","spaghetti"], "misalignment":["layer_shift"] }
DECK_RECIPES = {  # absolute setpoints, from the deck
  "over_extrusion": {"nozzle_temp":190,"speed":95,"flow":80},
  "under_extrusion":{"nozzle_temp":205,"speed":80,"flow":110},
  "stringing":      {"nozzle_temp":190,"speed":80,"flow":95},
  "warping":        {"bed_temp":65} }
```

## §Config (`config/default.yaml`; loaded by `xqi.config.load(path) -> Config`, a nested frozen dataclass)
```yaml
mode: advisory                     # baseline | gated-recipe | auto | advisory
run_dir: runs
printer: {kind: octoprint, url: "http://octopi.local", api_key_env: XQI_OCTOPRINT_KEY,
          timeout_s: 0.5, poll_s: 1.0,
          nominal: {nozzle_temp: 210, bed_temp: 60, flow: 100, speed: 100}}   # kind: octoprint | fake
camera: {source: "0", width: 1920, height: 1056, max_gap_s: 3.0}             # "0" | "replay:<dir>"
detector: {weights: models/yolo/best.pt, imgsz: 1088, conf: 0.25, device: "cuda:0"}
confirm: {hits: {clog: 2, layer_shift: 2, spaghetti: 2, over_extrusion: 3, under_extrusion: 4,
                 stringing: 3, warping: 3}, rearm_frames: 50}                 # [assumed] until REU values ported
critical: {clog: estop, layer_shift: estop, spaghetti: estop}                 # estop | pause (ADR-0006)
severity: {a_ref: 0.02, h_ref: 15, window: 30}
causes_file: config/causes.yaml
cause_model: {weights: models/cause/final.pt, crop_pad: 0.2, input_px: 224, device: "cuda:0"}
conformal: {alpha: 0.10, qhat_file: models/cause/qhat.json}
correction: {d_min: {nozzle_temp: 2, bed_temp: 2, flow: 5, speed: 5},
             d_max: {nozzle_temp: 5, bed_temp: 5, flow: 10, speed: 10}}
envelope:
  L1: {nozzle_temp: [170, 240], bed_temp: [0, 100], flow: [50, 150], speed: [50, 150]}
  L2: {step: {nozzle_temp: 5, bed_temp: 5, flow: 10, speed: 10},
       cooldown_s: {nozzle_temp: 45, bed_temp: 90, flow: 20, speed: 20}}
  L3: {material: PLA, window: {nozzle_temp: [195, 225], bed_temp: [50, 70], flow: [90, 110], speed: [80, 110]}}
  L4: {tau: 0.60}
sensors: {temp_dev_c: 5, temp_dev_s: 10, settle_s: {nozzle_temp: 45, bed_temp: 90}}
hitl: {timeout_s: 90, timeout_action: noop}                                   # noop | pause
verify: {window_s: 120, settle_s: 30}
attribution: {enabled: true, layer: "model.model.9"}                          # YOLO11 SPPF output, [assumed]
```
Validation rules: every `Var` key present in each per-var map; `d_max ≤ L2.step`; L3 ⊆ L1; hits ≥ 1; mode in enum. A violation raises `ConfigError` naming the key.

## §Data (canonical files written by scripts/adapt_trials.py; the adapter hides the REU format)
- `data/trials.csv`: `trial_id, printer, geometry, material, t_start_iso, t_end_iso, cause, var, direction, magnitude, unit, notes`. `cause ∈ CAUSES`; magnitude is signed in °C or pp; one row per induced cause; co-occurring causes = multiple rows with the same trial_id.
- `data/images.csv`: `image_path, label_path, printer, geometry, trial_id, ts_iso, reu_split` (reu_split ∈ train/val/test).
- `data/crops.csv`: `crop_path, image_path, box_idx, defect, cause, trial_id, geometry, printer, area_frac` (only boxes with an unambiguous cause; dropped boxes are counted in the audit report).
- `data/splits/logo.json`: `{"version":1, "folds":[{"test_geometry":"g1","train_trials":[...],"calib_trials":[...],"test_trials":[...]}...]}`. Committed and frozen.
- Label assignment rule: a box of class k in trial t gets cause c iff c ∈ causes(t) and k ∈ CAUSE_DEFECTS[c], and exactly one such c exists. If none: `none` (only when the trial has no induced cause). Otherwise: dropped as ambiguous.

## §Store (`runs/<run_id>/events.sqlite`, WAL; `xqi/store.py`)
| Table | Columns (all rows also have `schema_version`, `run_id`) | Writer |
|---|---|---|
| runs | run_id PK, mode, cfg_json, git_sha, started_iso, ended_iso | loop |
| detections | frame_id, ts, cls, conf, x1,y1,x2,y2, area_frac | loop |
| telemetry | ts, state, nozzle_actual_c, nozzle_target_c, bed_actual_c, bed_target_c, flow_pct, speed_pct | loop |
| defects | defect_id PK, cls, frame_id, t0, t_conf, conf, bbox_json, severity, critical, crop_path, heatmap_path | loop |
| explanations | defect_id, probs_json, set_json, qhat, flags_json, t_cause | loop |
| proposals | proposal_id PK, defect_id, cause, var, from_value, delta, to_value, gcode_json, counterfactual, gate_json, passed | loop |
| verdicts | defect_id, verdict, reason, proposal_ids_json, t_gate, pending, deadline_ts | loop |
| operator_decisions | id PK, defect_id, proposal_id, choice, modified_delta, operator, wall_iso, latency_s, consumed | **UI** (insert); loop sets `consumed` only |
| actions | action_id PK, defect_id, proposal_id, source (auto/operator/critical/baseline/timeout), gcode_json, t_disp, ok | loop |
| outcomes | action_id, defect_id, cls, verdict, r_before, r_after, window_s | loop |
| timings | defect_id, stage, t | loop |
| alerts | ts, kind, message | loop |

`Store(path)` API: `write_<table>(obj)` per table, `pending_events()`, `new_decisions()`, `mark_consumed(id)`, `query(sql, params)` (read-only helper for scripts/UI).

## §Module APIs
```python
# xqi/config.py
load(path: str | Path) -> Config
# xqi/printer.py
class Printer(Protocol):
    def get_state(self) -> PrinterState: ...
    def send_gcode(self, lines: Sequence[str]) -> bool: ...     # True on 2xx
    def pause(self) -> bool: ...; def resume(self) -> bool: ...; def estop(self) -> bool: ...  # estop = M112
class FakePrinter(Printer): sent: list[tuple[float, str]]       # §12 thermal model; tracks M104/M140/M220/M221
class OctoPrintClient(Printer): ...                             # GET /api/printer, POST /api/printer/command, POST /api/job {"command":"pause","action":"pause"}
# xqi/camera.py
open_source(spec: str, width: int, height: int) -> Iterator[Frame]
# xqi/detect.py
class Detector: __init__(weights, imgsz, conf, device); __call__(frame: Frame) -> list[Detection]
class ConfirmationTracker: __init__(hits: dict, rearm_frames: int, severity_cfg); update(frame, dets) -> list[ConfirmedDefect]
# xqi/explain/cause_model.py
class CauseModel: __init__(weights, causes, defects, device); predict(crop_bgr: np.ndarray, defect: str) -> CauseEstimate
build_model(n_causes: int, n_defects: int) -> torch.nn.Module
# xqi/explain/conformal.py
calibrate(probs: np.ndarray, y: np.ndarray, alpha: float) -> float
predict_set(probs: np.ndarray, qhat: float, labels: Sequence[str]) -> tuple[str, ...]
# xqi/explain/counterfactual.py
make_proposal(cause: str, p: float, severity: float, state: PrinterState, cfg) -> Proposal | None
recipe_to_proposals(defect: str, state: PrinterState, defect_id: str) -> list[Proposal]
# xqi/explain/sensors.py
check(history: Sequence[PrinterState], now: float, cfg) -> tuple[str, ...]
# xqi/explain/attribution.py
eigencam(model, frame: Frame, layer: str, xyxy) -> np.ndarray   # float32 [0,1], crop-sized
# xqi/explain/__init__.py
class Explainer: explain(cd: ConfirmedDefect, frame: Frame, history) -> tuple[CauseEstimate, CauseSet, tuple[str,...], list[Proposal]]
crop(image, xyxy, pad: float) -> np.ndarray
# xqi/gate.py
gate(p: Proposal, state: PrinterState | None, now: float, cfg) -> GateDecision
event_verdict(mode, cd, cset: CauseSet | None, est: CauseEstimate | None, flags, decisions: list[GateDecision], state, cfg) -> EventVerdict
# xqi/verify.py
class Verifier: watch(action_id, defect_id, cls, t_a); tick(frame_ts, present: set[str]) -> list[Outcome]; close() -> list[Outcome]
# xqi/orchestrator.py
class Orchestrator: __init__(cfg, printer, source, detector, explainer, store); run(max_frames: int | None = None) -> None
```

## §CLI (`python -m xqi <cmd>`, argparse)
`run --config C [--mode M] [--max-frames N]` · `ui --run R` (wraps `streamlit run xqi/ui.py -- --run R`) · `study --events R --out S` · `recalibrate --run R` (COULD)

## Versioning rule
`SCHEMA_VERSION` lives in `xqi/types.py` and goes into every store row. A breaking change to §Types, §Store or §Data means: bump it, and record it as a DESCEND in LOGBOOK.md. Never silently.
