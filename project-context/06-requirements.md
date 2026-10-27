<!-- HEAD
FILE:     06-requirements.md
PHASE:    2 — SPECIFY (delta 2026-10-27, ADR-0009 software-only)
UPDATED:  2026-10-27
STATUS:   accepted delta (user approved ADR-0009 recommendations 2026-10-27)
SUMMARY:  Software only. Two paths share one explain → gate → HITL stack:
          reactive (pluggable detector → confirm → explain) and proactive (cause model on the nozzle
          ROI every n frames → EWMA early warning → proposal card, never auto-applied, FR-029/030).
          Cause ground truth = CAXTON parameter classes (FR-031); eval = leave-parts-out folds.
          Hardware, printer link and rig runs belong to the integrating team (hand-off FR-032).
          Floor = training-fold majority cause. NFR-001 ≤ 30 ms p95 action path (offline bench);
          NFR-012 proactive warning. Rig NFRs (old 002/003/010) re-scoped to the offline replay.
OPEN:     Thresholds marked [assumed] until Dr. Meti signs (ADR-0009 Q5).
-->

# Requirements

Notation: `cfg.x` = key in `config/default.yaml` (09-interfaces §Config). Formulas live in `07-math.md`.

## Functional

```
FR-001 | Run in one of four modes: baseline, gated-recipe, auto, advisory
  Priority:   MUST
  Rationale:  ADR-0001; the integrating team picks the mode for their rig; offline we A/B on replay
  Acceptance: GIVEN cfg.mode=X WHEN `python -m xqi run --config ...` starts THEN the run
              header row in the store records mode=X and only X's action path executes
  Verified by: tests/test_orchestrator.py::test_modes
```
```
FR-002 | Acquire frames from an OpenCV camera index, a replay folder (sorted by filename), or a CAXTON print
         (`caxton:<crops.csv>#<trial_id>`, rows in timestamp order)
  Priority:   MUST
  Rationale:  offline/CI runs and the CAXTON HITL replay; the camera index is for the integrating team
  Acceptance: GIVEN cfg.camera.source="replay:<dir>" WHEN iterated THEN yields Frame objects in
              filename order with monotonically increasing ts, then stops. GIVEN "caxton:<csv>#p7" THEN yields
              print p7's crops in ts order, and the FakePrinter's process values follow each row (T-0062)
  Verified by: tests/test_camera.py
```
```
FR-003 | Detect defects with whatever YOLO weights cfg.detector.weights names (pluggable; null = no detector)
  Priority:   MUST
  Rationale:  ADR-0009 D3: detection is an input the integrating team supplies; AM_1 is a placeholder.
              We train no detector (no box labels exist).
  Acceptance: GIVEN a frame WHEN detect() runs THEN returns list[Detection] with cls in DEFECTS,
              conf in [0,1], xyxy in pixel coords, area_frac in (0,1]
  Verified by: tests/test_detect.py (fake model); real weights are the integrating team's check (docs/HANDOFF.md)
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
  Rationale:  ADR-0002. CAXTON has no defect class, so cfg.cause_model.use_defect=false drops the defect
              one-hot (the predict signature is unchanged; the argument is ignored)
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
FR-009 | Save an EigenCAM heatmap PNG (cause-model backbone, cfg.attribution.layer) per non-critical event
         (confirmed defect or early warning), computed after dispatch
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
              (M221 up, M104 up) with Δ per 07 §2; `none` → no proposal; a manual cause (z_offset_low/high,
              misalignment; 09 MANUAL_ADVICE) → no setpoint proposal, its advice text goes on the card and
              the event ESCALATEs (07 §4 row 7)
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
FR-018 | Pause → Printer.pause(); Stop → Printer.estop() (M112) only after a confirm dialog
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
FR-024 | Offline evaluation scripts write reports/*.md: data audit, L3 window, cause (floor vs model),
         conformal, counterfactual fidelity, proactive warning, recipe audit, latency, demo, study, acceptance
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
FR-027 | (dropped 2026-10-27, ADR-0009: detector work belongs to the integrating team)
  Priority:   WON'T
```
```
FR-028 | Domain-shift check: run the final cause model on the inherited camera roll (whole-bed view, other
         printer) and report set sizes and the cause distribution (ADR-0009 D6)
  Priority:   COULD
```
```
FR-029 | Proactive early warning: every cfg.proactive.every_n frames, run the cause model on the nozzle ROI
         (cfg.proactive.roi; null = whole frame), smooth per-cause probabilities and raise an early warning
         for cause c per 07 §13, with no confirmed defect needed
  Priority:   MUST
  Rationale:  ADR-0009 D4: "proactiveness" = warn and propose before a defect is visible to the detector
  Acceptance: GIVEN p_flow_low = 0.9 for m consecutive evaluations WHEN updated THEN exactly one warning
              (cause=flow_low); none again until p̄ < θ_off and the cooldown has passed; `none` never warns
  Verified by: tests/test_proactive.py
```
```
FR-030 | An early warning becomes an event (defects row, cls = "early_warning") that goes through the same
         conformal set → proposals → gate path and is always shown as PROPOSE (or ESCALATE), never APPLY
  Priority:   MUST
  Rationale:  ADR-0009 Q3: proactive actions need human approval; the gate still applies
  Acceptance: GIVEN mode=auto and a warning whose proposal passes L1–L4 WHEN handled THEN verdict = PROPOSE and
              no G-code is sent until an operator Apply
  Verified by: tests/test_orchestrator.py::test_early_warning_never_auto
```
```
FR-031 | Adapt CAXTON to the canonical data files: per-print trials.csv, per-image images.csv with the four
         parameter classes and a single cause label, a part-stratified subset, and 224 px nozzle-ROI crops
  Priority:   MUST
  Rationale:  ADR-0009 D2: the only cause-labelled source
  Acceptance: per 09 §Data; label rule 07 §15; prints 183–191 and z_offset < 0.08 mm excluded by default and counted
  Verified by: tests/test_adapt_caxton.py, tests/test_build_crops.py (synthetic fixtures)
```
```
FR-032 | Hand-off package for the integrating team: docs/HANDOFF.md (Printer protocol, Detector contract,
         recommendation/store contract, the config keys they own) and a Printer conformance test they run
         against their own implementation
  Priority:   MUST
  Rationale:  ADR-0009 D1/Q4: the Printer protocol is the boundary
  Verified by: tests/test_printer_contract.py passes for FakePrinter
```

## Non-functional (each has a number)
| ID | Requirement | Number | Verified by |
|---|---|---|---|
| NFR-001 | Added action-path latency (crop + cause model + conformal + gate) | p95 ≤ **30 ms** on the RTX 3050 4 GB | scripts/eval_latency.py --bench (T-0036) |
| NFR-002 | Frame → verdict, offline replay (CAXTON source + FakePrinter, real model) | p95 ≤ **0.30 s** | T-0066 store timings |
| NFR-003 | Event → card visible in the dashboard, offline replay | p95 ≤ **1.0 s** | T-0066 store timestamps |
| NFR-004 | Post-gate envelope violations | **0** in 100 000 random cases + all offline runs | T-0023, T-0066 |
| NFR-005 | Cause top-1 (leave-parts-out mean, bootstrap 95 % CI over prints) / top-3 | ≥ floor + **10 pp** / ≥ **0.90** | T-0013 |
| NFR-006 | Conformal empirical coverage @ α = 0.10 / mean set size | ≥ **0.85** / ≤ **2.0** | T-0015 |
| NFR-007 | Counterfactual direction fidelity on confident events (07 §9) | ≥ **0.85**, confident fraction reported | T-0017 |
| NFR-008 | Soak: replay + FakePrinter | **2 h**, no crash, RSS growth < **200 MB** | T-0052 (`slow`) |
| NFR-009 | Unit suite runtime (excluding `gpu`/`hw`/`slow` markers) | < **120 s** on CPU | CI command in CLAUDE.md |
| NFR-010 | (dropped: rig resolution rate is the integrating team's measurement) | — | — |
| NFR-011 | GPU memory at inference (cause model; + detector when configured) | ≤ **3.5 GB** | T-0036 |
| NFR-012 | Proactive warning on held-out prints (07 §14) | median time-to-warning ≤ **10 s**; onset recall@30 s ≥ **0.70**; false warnings ≤ **1 / print-hour** [assumed] | T-0063 |

## Baseline, oracle, frozen eval
- **Floor (cause):** predict the most frequent cause of the training folds' images (CAXTON has no defect class).
  ADR-0002 option 1 (prior + sensors) is not a fair floor here: the sensor values ARE the labels.
- **Reference (not a floor):** the paper's random-by-image protocol on fold 0, if time allows, to show the
  within-print leakage gap (T-0013, SHOULD).
- **Floor (proactive):** the same warning rule on the raw (unsmoothed) probabilities; shows what smoothing buys.
- **Oracle (cause):** the CAXTON parameter class (accuracy 1.0). Results reported as gap-to-oracle.
- **Frozen eval (committed in T-0007, not edited afterwards):**

| Item | Value |
|---|---|
| Split | leave-parts-out, 5 folds (GroupKFold by print = part, seed 0), calibration = 20 % of training prints (ADR-0007 re-scoped) |
| Cause metrics | top-1, top-3, per-class recall, gap to floor, bootstrap 95 % CI over test prints |
| Conformal | coverage and mean set size at α ∈ {0.05, 0.10, 0.20} |
| Counterfactual | direction fidelity on confident events, confident fraction |
| Proactive | time-to-warning, onset recall@30 s, false warnings / print-hour; θ_on chosen on calibration prints only |
| Gate | violations / 100 000 |
| Thresholds | NFR-004..NFR-007, NFR-012 |
| Verdict owner | Dr. Vinod Kumar V Meti |

## Non-goals (WON'T)
- Anything physical (ADR-0009 D1): printer connection, OctoPrint/G-code transport testing, camera or Raspberry Pi
  choice, rig runs, induced-defect printing, envelope sign-off for a real printer. The integrating team owns these.
- Training or evaluating a defect detector (no box labels exist).
- A multi-head per-parameter model (the paper's design), unless the T-0006 audit shows too few single-deviation
  images (then DESCEND).
- RL or adaptive policy learning beyond FR-026 recalibration (deck WP3 "learning" is out).
- Firmware modification, new sensors (thermal, acoustic, humidity), multi-printer fleet, cloud.
- Changes to the detector architecture, or claims about detection uncertainty (that's 4.1.1).
- A new DOE sweep; L3 is derived from CAXTON's "good" class ranges (T-0024).
- Image-generative counterfactuals.
