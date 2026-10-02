<!-- HEAD
FILE:     06-requirements.md
PHASE:    2 — SPECIFY
UPDATED:  2026-10-03
STATUS:   draft (awaiting gate)
SUMMARY:  25 MUST/SHOULD FRs, 3 COULD, 1 WON'T block; 11 NFRs, each with a number.
          Pipeline: frames -> YOLO11-S -> confirm -> (critical: estop/pause) | cause
          model -> conformal set -> proposals -> 4-layer gate -> APPLY / PROPOSE /
          ESCALATE / NOOP -> dashboard -> outcome check. Floor = majority cause per
          defect class; oracle = induced cause; frozen eval = LOGO by trial,
          thresholds in §Frozen eval. Latency: added action path <= 30 ms p95,
          end-to-end auto p95 <= 0.30 s.
OPEN:     Thresholds are proposals until Dr. Meti signs the gate.
-->

# Requirements

Notation: `cfg.x` = key in `config/default.yaml` (09-interfaces §Config). Formulas live in `07-math.md`.

## Functional

```
FR-001 | Run in one of four modes: baseline, gated-recipe, auto, advisory
  Priority:   MUST
  Rationale:  ADR-0001; every claim is an A/B on the same rig
  Acceptance: GIVEN cfg.mode=X WHEN `python -m xqi run --config ...` starts THEN the run
              header row in the store records mode=X and only X's action path executes
  Verified by: tests/test_orchestrator.py::test_modes
```
```
FR-002 | Acquire frames from an OpenCV camera index or a replay folder (sorted by filename)
  Priority:   MUST
  Rationale:  rig runs + offline/CI runs
  Acceptance: GIVEN cfg.camera.source="replay:<dir>" WHEN iterated THEN yields Frame objects in
              filename order with monotonically increasing ts, then stops
  Verified by: tests/test_camera.py
```
```
FR-003 | Detect defects with the YOLO11-S weights at cfg.detector.imgsz and conf >= cfg.detector.conf
  Priority:   MUST
  Rationale:  inherited detector
  Acceptance: GIVEN a frame WHEN detect() runs THEN returns list[Detection] with cls in DEFECTS,
              conf in [0,1], xyxy in pixel coords, area_frac in (0,1]
  Verified by: tests/test_detect.py (fake model) + scripts/eval_detector.py (real weights)
```
```
FR-004 | Confirm a defect after cfg.confirm.hits[cls] consecutive frames; fire once per episode
  Priority:   MUST
  Rationale:  deck multi-frame logic (2–4 hits)
  Acceptance: GIVEN hits[stringing]=3 WHEN stringing appears in frames 1,2,3 THEN exactly one
              ConfirmedDefect at frame 3; a miss resets the count; no re-fire until the class
              has been absent for cfg.confirm.rearm_frames frames
  Verified by: tests/test_confirm.py
```
```
FR-005 | Critical classes (cfg.critical) trigger their configured action (estop=M112 | pause) before any explanation work
  Priority:   MUST
  Rationale:  ADR-0006, deck safety response
  Acceptance: GIVEN confirmed spaghetti WHEN handled THEN the printer receives M112 (or pause) and
              the action row's timestamp precedes the explanation row's
  Verified by: tests/test_orchestrator.py::test_critical_first
```
```
FR-006 | Compute severity s in [0,1] for every confirmed defect (07 §1)
  Priority:   MUST
  Rationale:  deck gap "not scaled to magnitude"
  Verified by: tests/test_explain.py::test_severity
```
```
FR-007 | Predict a probability vector over CAUSES from (crop, defect class)
  Priority:   MUST
  Rationale:  ADR-0002
  Acceptance: GIVEN a crop WHEN predict() THEN probs sum to 1±1e-5 over cfg CAUSES order; no
              telemetry or setpoint enters the model
  Verified by: tests/test_cause_model.py (signature test asserts the inputs)
```
```
FR-008 | Return a conformal cause set at risk cfg.conformal.alpha using a stored qhat
  Priority:   MUST
  Rationale:  ADR-0003
  Verified by: tests/test_conformal.py
```
```
FR-009 | Save an EigenCAM heatmap PNG per non-critical confirmed defect, computed after dispatch
  Priority:   SHOULD
  Rationale:  "where" evidence for the operator; D10 keeps it off the latency path
  Acceptance: GIVEN a confirmed defect WHEN processed THEN runs/<id>/heatmaps/<defect_id>.png
              exists and its timestamp is after the decision row's
  Verified by: tests/test_attribution.py
```
```
FR-010 | Run sensor checks on PrinterState and attach flags (07 §5)
  Priority:   MUST
  Rationale:  telemetry evidence without model leakage; heater faults are not visible in the image
  Acceptance: GIVEN nozzle actual-target deviation > cfg.sensors.temp_dev_c for
              > cfg.sensors.temp_dev_s WHEN checked THEN flag "heater_deviation:nozzle"; any flag
              blocks APPLY
  Verified by: tests/test_sensors.py
```
```
FR-011 | Generate one Proposal per actionable cause in the set (07 §2), with G-code and counterfactual text
  Priority:   MUST
  Rationale:  "range of solutions"
  Acceptance: GIVEN set {flow_low, nozzle_temp_low} WHEN proposals generated THEN two proposals
              (M221 up, M104 up) with Δ per 07 §2; `none` → no proposal; `misalignment` → no setpoint
              proposal, forces ESCALATE
  Verified by: tests/test_counterfactual.py
```
```
FR-012 | Gate every proposal through L1–L4 (ADR-0004, 07 §3)
  Priority:   MUST
  Verified by: tests/test_gate.py, tests/test_gate_property.py
```
```
FR-013 | Decide the event verdict APPLY / PROPOSE / ESCALATE / NOOP (07 §4)
  Priority:   MUST
  Acceptance: matches the truth table in 07 §4 for all rows
  Verified by: tests/test_gate.py::test_event_verdict_table
```
```
FR-014 | On APPLY (auto) or an operator Apply, send the gated G-code, update tracked setpoints, start the cooldown
  Priority:   MUST
  Verified by: tests/test_orchestrator.py::test_apply_updates_state
```
```
FR-015 | Dashboard live view: latest frame with boxes, printer state, mode, event timeline
  Priority:   MUST
  Verified by: manual check script in T-0037 + tests on the data-access function
```
```
FR-016 | Proposal card per pending event: defect, severity, crop + heatmap, cause set with probabilities,
         sensor flags, each proposal's from→to, gate reasons, counterfactual sentence; buttons
         Apply / Modify / Reject / Pause / Stop
  Priority:   MUST
  Verified by: tests/test_ui_data.py + T-0038 demo
```
```
FR-017 | An operator Modify value is re-gated in the loop process before dispatch
  Priority:   MUST
  Rationale:  trust boundary (UI is not trusted)
  Acceptance: GIVEN Modify Δ beyond L2 WHEN the loop processes it THEN Δ is clipped and the reason is logged
  Verified by: tests/test_orchestrator.py::test_modify_regated
```
```
FR-018 | Pause → OctoPrint job pause; Stop → M112 only after a confirm dialog
  Priority:   MUST
  Verified by: tests/test_orchestrator.py::test_pause_stop
```
```
FR-019 | If no operator response in cfg.hitl.timeout_s, execute cfg.hitl.timeout_action (noop | pause) and log choice=timeout
  Priority:   MUST
  Verified by: tests/test_orchestrator.py::test_timeout
```
```
FR-020 | After each applied action, classify the outcome resolved / persisted / worsened (07 §6)
  Priority:   MUST
  Verified by: tests/test_verify.py
```
```
FR-021 | Persist every stage to runs/<run_id>/events.sqlite with schema_version (09 §Store)
  Priority:   MUST
  Verified by: tests/test_store.py
```
```
FR-022 | Log per-stage monotonic timings for every confirmed defect (07 §7)
  Priority:   MUST
  Verified by: tests/test_orchestrator.py::test_timings_logged
```
```
FR-023 | Baseline mode reproduces deck behaviour: deck recipes (absolute setpoints) + M112, no gate
  Priority:   MUST
  Verified by: tests/test_orchestrator.py::test_baseline_parity
```
```
FR-024 | Offline evaluation scripts write reports/*.md: detector, data audit, cause (floor vs model),
         conformal, counterfactual fidelity, recipe audit, latency, rig results, study, acceptance
  Priority:   MUST
  Verified by: each script's ticket
```
```
FR-025 | Study mode: replay logged events to a participant with explanation ON/OFF (counterbalanced),
         recording choice, decision time, NASA-TLX and a 5-item trust scale
  Priority:   SHOULD
  Verified by: tests/test_study.py + T-0045 pilot
```
```
FR-026 | Recalibrate qhat from newly labelled logged events (`python -m xqi recalibrate`)
  Priority:   COULD
```
```
FR-027 | Tiled (SAHI-style) inference experiment for under-extrusion
  Priority:   COULD
```
```
FR-028 | Leave-one-printer-out cause evaluation (Kobra 2 Neo)
  Priority:   COULD
```

## Non-functional (each has a number)
| ID | Requirement | Number | Verified by |
|---|---|---|---|
| NFR-001 | Added action-path latency (crop + cause model + conformal + gate) | p95 ≤ **30 ms** on the RTX 3050 4 GB | scripts/eval_latency.py (T-0036) |
| NFR-002 | First defect frame → command dispatched, auto mode | p95 ≤ **0.30 s**; critical path p95 ≤ **0.27 s** | T-0036, T-0039 rig |
| NFR-003 | Confirmation → card visible in the dashboard | p95 ≤ **1.0 s** | T-0039 rig (store timestamps) |
| NFR-004 | Post-gate envelope violations | **0** in 100 000 random cases + all rig runs | T-0023, T-0042 |
| NFR-005 | Cause top-1 (LOGO mean) / top-3 | ≥ floor + **10 pp** / ≥ **0.90** | T-0013 |
| NFR-006 | Conformal empirical coverage @ α = 0.10 / mean set size | ≥ **0.85** / ≤ **2.0** | T-0015 |
| NFR-007 | Counterfactual direction fidelity | ≥ **0.85** | T-0017 |
| NFR-008 | Soak: replay + FakePrinter | **2 h**, no crash, RSS growth < **200 MB** | T-0034 soak test (marked `slow`) |
| NFR-009 | Unit suite runtime (excluding `gpu`/`hw`/`slow` markers) | < **120 s** on CPU | CI command in CLAUDE.md |
| NFR-010 | Rig resolution rate (auto vs baseline) / setpoint reversals per run | ≥ baseline − **5 pp** / ≤ baseline | T-0042 |
| NFR-011 | GPU memory, YOLO11-S + cause model at inference | ≤ **3.5 GB** | T-0036 |

## Baseline, oracle, frozen eval
- **Floor (cause):** for each defect class, predict the most frequent induced cause in the training folds. This equals the cause implied by the deck's fixed recipe per class.
- **Floor (correction):** `baseline` mode, i.e. the deck's recipes.
- **Oracle (cause):** the induced cause (accuracy 1.0). Results are reported as gap-to-oracle.
- **Oracle (correction):** the inverse of the induced deviation applied exactly (from the campaign log). Rig resolution under the oracle is measured on ≥ 1 run per cause in T-0041 where feasible.
- **Frozen eval (committed in T-0007, not edited afterwards):**

| Item | Value |
|---|---|
| Split | LOGO, 8 folds, calibration 20 % by trial inside the training geometries (ADR-0007) |
| Cause metrics | top-1, top-3, per-class recall, gap to floor |
| Conformal | coverage and mean set size at α ∈ {0.05, 0.10, 0.20} |
| Counterfactual | direction fidelity on top-1 |
| Gate | violations / 100 000 |
| Rig | resolution rate, reversals, max setpoint deviation, latency p95, by mode |
| Thresholds | NFR-004..NFR-007, NFR-010 |
| Verdict owner | Dr. Vinod Kumar V Meti |

## Non-goals (WON'T)
- RL or adaptive policy learning beyond FR-026 recalibration (deck WP3 "learning" is out).
- Firmware modification, new sensors (thermal, acoustic, humidity), multi-printer fleet, cloud.
- Changes to the detector architecture, or claims about detection uncertainty (that's 4.1.1).
- A new DOE sweep; L3 is derived from existing trial data (T-0024).
- Image-generative counterfactuals.
