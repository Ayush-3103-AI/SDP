# xqi hand-off: for the integrating team

This is for the engineers who connect `xqi` to a real printer and camera. It covers what xqi does, what you
implement and supply, what you own and sign off, and what you receive. The spec it follows is
`project-context/09-interfaces.md` §Hand-off (ADR-0009 Q4).

## 1. What xqi does

xqi watches an FFF print through a camera and proposes **explained, gated** setpoint corrections to a human.

- **Reactive path.** Your detector finds a defect (for example `under_extrusion`). The tracker confirms it over a
  few frames. The cause model reads the image crop and gives a probability for each process cause
  (`flow_low`, `nozzle_temp_high`, …). A conformal set keeps the causes it cannot rule out (α = 0.10). Each
  actionable cause becomes a proposal (for example `M221 S108`) with a counterfactual sentence.
- **Proactive path (early warning).** Every `proactive.every_n` frames, the cause model reads the nozzle ROI. When
  a smoothed cause probability stays high, xqi raises an early warning before a defect is visible. **An early
  warning is never applied automatically.** It is always a card for a human (FR-030).
- **Safety gate.** Every proposal passes `xqi.gate.gate()` before anything moves the printer: L2 step and
  cooldown, L1 machine limits, L3 characterised window, then L4 confidence (ADR-0004). It is pure and fails
  closed: missing or NaN state escalates.
- **Human in the loop.** The dashboard shows a card per event: the cause set, the heatmap, the gate reasons, and
  Apply / Modify / Reject / Pause / Stop. The loop re-gates every Apply and Modify against the current state.
- **Record.** Every frame-level decision goes into `runs/<run_id>/events.sqlite` (§7).

xqi does not train your detector, test your printer transport, or sign off your envelope.

## 2. What you implement: a `Printer`

`xqi.printer.Printer` (a `typing.Protocol`). The docstring in `xqi/printer.py` is the normative text.

| Method | Returns | Semantics |
|---|---|---|
| `get_state()` | `PrinterState` | A fresh reading. Temperatures in **°C**. `flow_pct` / `speed_pct` in **% of the sliced value** (the M221 / M220 `S` value; 100 = as sliced). `ts` and `last_change_ts` on **`time.monotonic()`**, the same clock as `Frame.ts`. `last_change_ts[v]` = when setpoint `v` last changed through `send_gcode` (key absent = never); the L2 cooldown reads it. On failure **raise `OSError`** (the loop sets state = None and escalates). Any other exception stops the loop. |
| `send_gcode(lines)` | `bool` | `True` once the printer accepted every line, `False` otherwise. **Never raise** for a refused or failed command. `M104` / `M140` / `M220` / `M221` must show in the next `get_state()` and in `last_change_ts`. The loop retries a `False` once, then logs `ok=0`. |
| `pause()` / `resume()` | `bool` | `True` if the printer is now paused / printing because of this call; `False` if refused (for example, already paused) or failed. Never raise. A failed pause makes the loop write a `pause_failed` alert. |
| `estop()` | `bool` | Stop motion and heaters **now**: M112 or your hardware equivalent. `True` once halted. Afterwards `send_gcode` returns `False` until a human resets the printer. |

Timeouts: each call should answer within `cfg.printer.timeout_s` (default 0.5 s). One retry inside the call is fine.
`xqi.printer.OctoPrintClient` is an unsupported reference implementation over the OctoPrint REST API.
`xqi.printer.FakePrinter` is the simulated printer that our tests use.

**Conformance.** `tests/test_printer_contract.py` checks the fields and units, the bool returns, that
M104/M221/M220 are reflected in the next `get_state`, and that refused commands do not raise. Point it at your
printer with a zero-argument factory:

```
XQI_PRINTER_IMPL=my_pkg.printer:make_printer uv run pytest tests/test_printer_contract.py
```

> ⚠ Against a real printer this test **heats the nozzle (M104 S205) and sends M112**. Run it with the printer
> attended, on a print you can lose, and never unattended (CLAUDE.md hard rule).

**Camera.** Either set `camera.source` to a camera index (`"0"`), or pass your own frame iterator to the
`Orchestrator` (§6). A frame is `xqi.types.Frame(frame_id, ts=time.monotonic(), wall_iso, image)`, where the
image is BGR `uint8`, H×W×3.

## 3. What you supply

### Detector (optional)
`detector.weights: null` (the default) means no detector. The reactive path is idle and the proactive path still
runs. To use yours, do one of these:
- Set `detector.weights` to an Ultralytics YOLO `.pt`. `xqi.detect.Detector` loads it. Its class names must map
  through `xqi.detect.normalise` to `DEFECTS` = `clog, layer_shift, over_extrusion, spaghetti, stringing,
  under_extrusion, warping`. Case, spaces and dashes are normalised. `over_extr` and `under_extr` are aliases.
  `no_defect`, `none`, `normal` and `good` are dropped. Any other name raises `ValueError` at start-up.
- Pass any callable `detector(frame) -> list[Detection]` to the `Orchestrator`. `Detection(frame_id, cls, conf,
  xyxy, area_frac)`: `cls` must be a `DEFECTS` entry, `xyxy` is in frame pixels, and `area_frac` is the box area
  divided by the frame area.

`confirm.hits` (frames per class before a defect is confirmed) and `severity.a_ref` depend on your detector and
camera. They are `[assumed]` defaults; recalibrate them.

### Nozzle ROI
`proactive.roi: [x1, y1, x2, y2]` in frame pixels (null = the whole frame). The cause model was trained on
CAXTON nozzle close-ups. The ROI must show the nozzle tip and the fresh extrudate at a similar scale. On a
different camera, re-check the domain gap (T-0067) before you trust the early warnings.

## 4. What you own and sign off

These keys in `config/default.yaml` are yours. Copy the file and change your copy.

| Key | Our default | Why this default | What you decide |
|---|---|---|---|
| `envelope.L1` | nozzle [170, 240] °C, bed [0, 100] °C, flow [50, 150] %, speed [50, 150] % | Generic hobby-printer machine limits | Your printer's real limits |
| `envelope.L2.step` / `cooldown_s` | step 5 °C / 5 °C / 10 % / 10 %; cooldown 45 / 90 / 20 / 20 s | One step at a time, slower for temperatures (thermal lag, 07 §12) | Steps and cooldowns your hardware settles within |
| `envelope.L3.window` | PLA: nozzle [195, 225], bed [50, 70], flow [90, 110], speed [80, 110] | The characterised process window (CAXTON "good" ranges, T-0024) | The window for your material and printer |
| `critical` | `estop` for clog, layer_shift and spaghetti | Matches the deck's M112 (ADR-0006) | `pause` if a clog is recoverable on your printer |
| `hitl.timeout_action` | `noop` | An unanswered card never moves the printer | `pause` if the printer can run unattended |

Constraint: `correction.d_max ≤ envelope.L2.step` and L3 ⊆ L1. `xqi.config.load` rejects a config that breaks
this and names the key.

## 5. What you receive

- The `xqi` package (Python 3.11, `uv sync`).
- `models/cause/final.pt` (cause-model checkpoint) and `models/cause/qhat.json` (conformal threshold). When they
  are missing, the loop logs one warning and escalates every non-critical defect.
- The store schema (§7) as the recommendation record.
- The dashboard: `uv run python -m xqi ui --run latest`. It is read-only, apart from the operator's decision rows.

## 6. How to run advisory mode

Advisory mode proposes and never applies on its own. Start with it.

With the built-in printers (`printer.kind: fake | octoprint`):

```
uv run python -m xqi run --config <your copy>.yaml --mode advisory
uv run python -m xqi ui --run latest          # second terminal
```

With your own `Printer`, call the loop directly:

```python
from dataclasses import replace
from pathlib import Path

from xqi.camera import open_source
from xqi.config import load
from xqi.explain import build_explainer
from xqi.orchestrator import Orchestrator, new_run_id
from xqi.store import Store

cfg = replace(load("my_config.yaml"), mode="advisory")
store = Store(Path(cfg.run_dir) / new_run_id() / "events.sqlite")
source = open_source(cfg.camera.source, cfg.camera.width, cfg.camera.height)   # or your own Frame iterator
Orchestrator(cfg, MyPrinter(), source, my_detector_or_None, build_explainer(cfg), store).run()
```

Modes: `advisory` (cards only), `auto` (applies a single confident reactive proposal that passed all four
layers; early warnings are still cards), `gated-recipe` and `baseline` (the deck's recipes, for comparison only).

## 7. The store: the recommendation record

`runs/<run_id>/events.sqlite` (SQLite, WAL). Every row carries `schema_version` (currently 2) and `run_id`.

| Table | What it records |
|---|---|
| `runs` | mode, the full config as JSON, git sha, start and end time |
| `detections` | every detector box per frame |
| `telemetry` | every `get_state()` reading |
| `defects` | each confirmed defect or early warning (`cls = early_warning`, `bbox_json` = null, severity = p̄), with crop and heatmap paths |
| `explanations` | cause probabilities, conformal set, q̂, sensor flags |
| `proposals` | each proposal, its G-code, counterfactual text, and the full gate result per layer |
| `verdicts` | the event verdict (CRITICAL / APPLY_RAW / APPLY / PROPOSE / ESCALATE / NOOP), its reason, pending and deadline |
| `operator_decisions` | apply / modify / reject / pause / stop from the UI, and `timeout` rows from the loop |
| `actions` | every command actually sent: source (auto / operator / critical / baseline / timeout), G-code, ok |
| `outcomes` | resolved / persisted / worsened / unknown after an applied action |
| `timings`, `alerts` | latency stages; camera gaps, failed pauses, blocked decisions |

The UI writes only `operator_decisions`. Everything else is written by the loop.

## 8. Safety rules (keep these when you integrate)

1. **Everything that moves the printer goes through `gate()`.** The only exceptions are the critical-class
   estop/pause (FR-005) and `baseline` mode.
2. **The UI never talks to the printer.** A button writes an `operator_decisions` row. The loop re-gates it on the
   current state and then acts.
3. **Early warnings are never auto-applied.** An early warning that escalates shows a card and does not pause.
4. **The cause model never sees setpoints or telemetry** (ADR-0002). `CauseModel.predict` takes only the image crop.
5. **The gate fails closed.** If `get_state` fails or returns NaN, the event escalates and nothing is sent.
6. Keep the OctoPrint key in the env var `XQI_OCTOPRINT_KEY`. Never put it in a config file or a log.
