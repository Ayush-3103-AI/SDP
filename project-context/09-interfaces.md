<!-- HEAD
FILE:     09-interfaces.md
PHASE:    2 — SPECIFY (delta 2026-10-27, ADR-0009)
UPDATED:  2026-10-27
STATUS:   accepted delta — SCHEMA_VERSION 2 (§Data rewritten for CAXTON; DESCEND logged)
SUMMARY:  Frozen contracts:
          §Types: dataclasses in xqi/types.py (+ CauseWarning). §Constants: DEFECTS (7), CAUSES (9, CAXTON
          taxonomy, frozen by T-0007), CAUSE_ACTION, MANUAL_ADVICE, EARLY_WARNING. §Config: default.yaml
          keys (+ proactive, use_defect, nullable detector). §Data: per-print trials.csv, per-image
          images.csv, crops.csv, splits/logo.json (leave-parts-out). §Store: 12 SQLite tables, single-writer.
          §Module APIs: one signature per module. §CLI: `python -m xqi <cmd>`. §Hand-off: what the
          integrating team implements and owns.
OPEN:     CAUSES finalised in T-0007 (edit config/causes.yaml, not code).
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
  xqi/proactive.py                                   (EarlyWarning, FR-029)
  scripts/  adapt_caxton.py build_crops.py audit_data.py derive_window.py make_splits.py eval_cause.py train_cause.py
            eval_conformal.py eval_counterfactual.py eval_proactive.py domain_shift.py gate_audit.py eval_latency.py
            analyze_study.py acceptance.py
  tests/    test_*.py   (markers: gpu, hw, slow)
  data/     (gitignored) caxton/ (raw, teammate laptop only) trials.csv images.csv crops/ crops.csv splits/ (splits/ IS committed)
  models/   (gitignored) yolo/<integrating team's weights> cause/*.pt cause/qhat.json cause/preds_*.npz
  runs/     (gitignored) <run_id>/events.sqlite heatmaps/ frames/
  reports/  *.md (committed)
  docs/     HANDOFF.md GPU_SETUP.md gpu-runs/ data/CAXTON.md study_protocol.md
  project-context/
```

## §Types (`xqi/types.py`, `@dataclass(frozen=True, slots=True)` unless noted)
```python
SCHEMA_VERSION = 2   # 2026-10-27: §Data rewritten for CAXTON (ADR-0009)
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
CauseWarning(cause: str, p: float, ts: float, probs: dict[str, float])     # 07 §13; p = smoothed p̄_c
```
Every dataclass has `to_dict()` / `from_dict()` that round-trip through JSON (numpy arrays excluded; `Frame.image` is never serialised).

## §Constants
```python
DEFECTS = ("clog","layer_shift","over_extrusion","spaghetti","stringing","under_extrusion","warping")
EARLY_WARNING = "early_warning"   # pseudo-class for FR-030 events; never in DEFECTS, never critical
# Loaded from config/causes.yaml, frozen by T-0007 (CAXTON taxonomy, 07 §15):
CAUSES = ("none","flow_low","flow_high","speed_low","speed_high",
          "nozzle_temp_low","nozzle_temp_high","z_offset_low","z_offset_high")
CAUSE_ACTION = {  # cause -> (var, d) with d=-1 low / +1 high; None = not a setpoint fix
  "flow_low":("flow",-1), "flow_high":("flow",+1), "speed_low":("speed",-1), "speed_high":("speed",+1),
  "nozzle_temp_low":("nozzle_temp",-1), "nozzle_temp_high":("nozzle_temp",+1),
  "none":None, "z_offset_low":None, "z_offset_high":None }
MANUAL_ADVICE = {  # manual causes (07 §2): card text, operator acts; event ESCALATEs
  "z_offset_low":  "Nozzle likely too close to the bed: raise the Z offset (babystep up ~0.05 mm) or re-level.",
  "z_offset_high": "Nozzle likely too far from the bed: lower the Z offset (babystep down ~0.05 mm) or re-level.",
  "misalignment":  "Possible layer shift: check belts and pulleys before resuming." }
CAUSE_DEFECTS = {  # [assumed] physics prior for the reactive path's card text and the detector-class audit only;
                   # no longer used for labels (CAXTON labels come from 07 §15)
  "nozzle_temp_high":["stringing","over_extrusion"], "nozzle_temp_low":["under_extrusion","clog"],
  "flow_high":["over_extrusion"], "flow_low":["under_extrusion"],
  "speed_high":["under_extrusion"], "speed_low":["over_extrusion","stringing"],
  "z_offset_low":["over_extrusion"], "z_offset_high":["under_extrusion","warping"] }
DECK_RECIPES = {  # absolute setpoints, from the deck (baseline mode, recipe audit)
  "over_extrusion": {"nozzle_temp":190,"speed":95,"flow":80},
  "under_extrusion":{"nozzle_temp":205,"speed":80,"flow":110},
  "stringing":      {"nozzle_temp":190,"speed":80,"flow":95},
  "warping":        {"bed_temp":65} }
```
`bed_temp_low` and `misalignment` left CAUSES (no CAXTON label). `bed_temp` stays a gate Var (deck recipes use it).

## §Config (`config/default.yaml`; loaded by `xqi.config.load(path) -> Config`, a nested frozen dataclass)
```yaml
mode: advisory                     # baseline | gated-recipe | auto | advisory
run_dir: runs
printer: {kind: fake, url: "http://octopi.local", api_key_env: XQI_OCTOPRINT_KEY,          # octoprint = unsupported reference
          timeout_s: 0.5, poll_s: 1.0,
          nominal: {nozzle_temp: 210, bed_temp: 60, flow: 100, speed: 100}}   # kind: octoprint | fake
camera: {source: "0", width: 1920, height: 1056, max_gap_s: 3.0}   # "0" | "replay:<dir>[@fps]" | "caxton:<crops.csv>#<trial_id>[@fps]"
detector: {weights: null, imgsz: 1088, conf: 0.25, device: "cuda:0"}         # null = no detector (proactive only); integrating team sets it
confirm: {hits: {clog: 2, layer_shift: 2, spaghetti: 2, over_extrusion: 3, under_extrusion: 4,
                 stringing: 3, warping: 3}, rearm_frames: 50}                 # [assumed] until REU values ported
critical: {clog: estop, layer_shift: estop, spaghetti: estop}                 # estop | pause (ADR-0006)
severity: {a_ref: 0.02, h_ref: 15, window: 30}
causes_file: config/causes.yaml
cause_model: {weights: models/cause/final.pt, crop_pad: 0.2, input_px: 224, device: "cuda:0", use_defect: false}
conformal: {alpha: 0.10, qhat_file: models/cause/qhat.json}
correction: {d_min: {nozzle_temp: 2, bed_temp: 2, flow: 5, speed: 5},
             d_max: {nozzle_temp: 5, bed_temp: 5, flow: 10, speed: 10}}
envelope:                          # defaults; the integrating team signs these off for their printer + material
  L1: {nozzle_temp: [170, 240], bed_temp: [0, 100], flow: [50, 150], speed: [50, 150]}
  L2: {step: {nozzle_temp: 5, bed_temp: 5, flow: 10, speed: 10},
       cooldown_s: {nozzle_temp: 45, bed_temp: 90, flow: 20, speed: 20}}
  L3: {material: PLA, window: {nozzle_temp: [195, 225], bed_temp: [50, 70], flow: [90, 110], speed: [80, 110]}}
  L4: {tau: 0.60}
sensors: {temp_dev_c: 5, temp_dev_s: 10, settle_s: {nozzle_temp: 45, bed_temp: 90}}
hitl: {timeout_s: 90, timeout_action: noop}                                   # noop | pause
verify: {window_s: 120, settle_s: 30}
attribution: {enabled: true, layer: "backbone.layer4"}                        # cause-model ResNet18 last block (07 §11)
proactive: {enabled: true, every_n: 1, roi: null, beta: 0.8, theta_on: 0.60, theta_off: 0.40, m: 3,
            cooldown_s: 60, max_gap_s: 10}                                   # 07 §13; roi = [x1,y1,x2,y2] px or null
```
Validation rules: every `Var` key present in each per-var map; `d_max ≤ L2.step`; L3 ⊆ L1; hits ≥ 1; mode in enum;
0 ≤ θ_off < θ_on ≤ 1; 0 ≤ β < 1; m ≥ 1; every_n ≥ 1. A violation raises `ConfigError` naming the key.

## §Data (canonical files; CAXTON adapter = scripts/adapt_caxton.py, P8; 07 §15)
Raw CAXTON stays on the teammate's GPU laptop under `data/caxton/` (never committed, never on the dev laptop).
- `data/trials.csv` (one row per print): `trial_id, printer, geometry, material, t_start_iso, t_end_iso, n_images, n_kept, source`.
  trial_id = `p<print_id>`; geometry = trial_id (each CAXTON print is a different part); printer = `unknown` unless the
  data names it; material = PLA; source = `caxton`.
- `data/images.csv` (one row per kept image): `image_path, trial_id, geometry, ts_iso, ts_s, flow_pct, speed_pct,
  z_offset_mm, nozzle_target_c, nozzle_c, bed_c, flow_cls, speed_cls, z_cls, nozzle_cls, cause, nozzle_x, nozzle_y`.
  ts_s = seconds since the print's first image; *_cls ∈ {0,1,2} = low/good/high; cause ∈ CAUSES ∪ {multi}.
- `data/crops.csv`: `crop_path, image_path, trial_id, geometry, ts_s, cause, flow_cls, speed_cls, z_cls, nozzle_cls,
  flow_pct, speed_pct, nozzle_target_c` (224 px ROI crops, P8; the process columns feed the replay, T-0062).
- `data/splits/logo.json`: `{"version":2, "kind":"leave-parts-out", "seed":0, "folds":[{"test_geometries":[...],
  "train_trials":[...], "calib_trials":[...], "test_trials":[...]}...]}`. 5 folds. Committed and frozen at T-0007.
- `models/cause/preds_fold{k}.npz`: `labels, probs_calib, y_calib, calib_trial, calib_ts, probs_test, y_test, test_trial,
  test_ts, test_cls` (test_cls = the four class columns, for 07 §14; y = −1 for `multi`). `preds_final.npz`: the final
  model's calibration split, same keys.
- `docs/data/CAXTON.md`: where the files came from (URLs, file names, sizes, sha256 of the CSV), licence text, date.

## §Store (`runs/<run_id>/events.sqlite`, WAL; `xqi/store.py`)
| Table | Columns (all rows also have `schema_version`, `run_id`) | Writer |
|---|---|---|
| runs | run_id PK, mode, cfg_json, git_sha, started_iso, ended_iso | loop |
| detections | frame_id, ts, cls, conf, x1,y1,x2,y2, area_frac | loop |
| telemetry | ts, state, nozzle_actual_c, nozzle_target_c, bed_actual_c, bed_target_c, flow_pct, speed_pct | loop |
| defects | defect_id PK, cls (a DEFECTS entry or `early_warning`), frame_id, t0, t_conf, conf, bbox_json (null for warnings), severity, critical, crop_path, heatmap_path | loop |
| explanations | defect_id, probs_json, set_json, qhat, flags_json, t_cause | loop |
| proposals | proposal_id PK, defect_id, cause, var, from_value, delta, to_value, gcode_json, counterfactual, gate_json, passed | loop |
| verdicts | defect_id, verdict, reason, proposal_ids_json, t_gate, pending, deadline_ts | loop |
| operator_decisions | id PK, defect_id, proposal_id, choice, modified_delta, operator, wall_iso, latency_s, consumed | **UI** (insert); loop sets `consumed`, and inserts `choice=timeout` rows (consumed=1) for FR-019 (D3, 2026-10-27) |
| actions | action_id PK, defect_id, proposal_id, source (auto/operator/critical/baseline/timeout), gcode_json, t_disp, ok | loop |
| outcomes | action_id, defect_id, cls, verdict, r_before, r_after, window_s | loop |
| timings | defect_id, stage, t | loop |
| alerts | ts, kind, message | loop |

`Store(path)` API: `write_<table>(obj)` per table, `pending_events()`, `new_decisions()`, `mark_consumed(id)`, `query(sql, params)` (read-only helper for scripts/UI).

## §Module APIs
```python
# xqi/config.py
load(path: str | Path) -> Config
load_causes(path: str | Path) -> Causes   # config/causes.yaml (cfg.causes_file); validated vs Var and DEFECTS
# xqi/printer.py
class Printer(Protocol):
    def get_state(self) -> PrinterState: ...
    def send_gcode(self, lines: Sequence[str]) -> bool: ...     # True on 2xx
    def pause(self) -> bool: ...; def resume(self) -> bool: ...; def estop(self) -> bool: ...  # estop = M112
class FakePrinter(Printer): sent: list[tuple[float, str]]       # §12 thermal model; tracks M104/M140/M220/M221
    set_process(flow: float, speed: float, nozzle_target: float) -> None   # CAXTON replay seeding (07 §12)
class OctoPrintClient(Printer): ...                             # GET /api/printer, POST /api/printer/command, POST /api/job {"command":"pause","action":"pause"}
# xqi/camera.py
open_source(spec: str, width: int, height: int, printer=None) -> Iterator[Frame]   # caxton: seeds printer.set_process per row
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
eigencam(model, frame: Frame, layer: str, xyxy) -> np.ndarray   # float32 [0,1], crop-sized; model = CauseModel.model
# xqi/explain/__init__.py
class Explainer: explain(cd: ConfirmedDefect, frame: Frame, history) -> tuple[CauseEstimate, CauseSet, tuple[str,...], list[Proposal]]
                 estimate(roi_bgr: np.ndarray) -> CauseEstimate          # cause model only (proactive path)
build_explainer(cfg) -> Explainer | None   # None + logged warning when final.pt or qhat.json is missing (D4)
crop(image, xyxy, pad: float) -> np.ndarray
# xqi/gate.py
gate(p: Proposal, state: PrinterState | None, now: float, cfg) -> GateDecision
event_verdict(mode, cd, cset: CauseSet | None, est: CauseEstimate | None, flags, decisions: list[GateDecision], state, cfg) -> EventVerdict
# xqi/proactive.py
class EarlyWarning: __init__(causes, cfg.proactive); update(ts: float, probs: dict[str,float]) -> list[CauseWarning]; reset()
# xqi/verify.py
class Verifier: watch(action_id, defect_id, cls, t_a); tick(frame_ts, present: set[str]) -> list[Outcome]; close() -> list[Outcome]
# xqi/orchestrator.py
class Orchestrator: __init__(cfg, printer, source, detector, explainer, store); run(max_frames: int | None = None) -> None
```

## §CLI (`python -m xqi <cmd>`, argparse)
`run --config C [--mode M] [--max-frames N]` · `ui --run R` (wraps `streamlit run xqi/ui.py -- --run R`) · `study --events R --out S` · `recalibrate --run R` (COULD)

## §Hand-off (what the integrating team implements and owns; docs/HANDOFF.md, T-0064)
- Implements: a `Printer` (get_state / send_gcode / pause / resume / estop) for their hardware, passing
  tests/test_printer_contract.py; optionally a camera index or their own frame iterator.
- Supplies: detector weights (cfg.detector.weights) with class names that `normalise` maps to DEFECTS; the nozzle ROI.
- Owns and signs off: envelope L1–L3 for their printer and material, cfg.critical actions, cfg.hitl.timeout_action.
- Receives: the `xqi` package, models/cause/final.pt + qhat.json, the store schema (§Store) as the recommendation
  record, and the dashboard. Anything that moves the printer goes through `gate()` (CLAUDE.md hard rule).

## Versioning rule
`SCHEMA_VERSION` lives in `xqi/types.py` and goes into every store row. A breaking change to §Types, §Store or §Data means: bump it, and record it as a DESCEND in LOGBOOK.md. Never silently.
