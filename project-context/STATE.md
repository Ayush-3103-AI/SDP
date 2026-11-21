# STATE — SDP: Explainable, safe HITL correction for FFF (CARR 4.1.3 slice), software only

PHASE:        5 — EXECUTE (re-planned per ADR-0009; delta gate APPROVED 2026-10-27).
LAST SESSION: 2026-11-21 (dev laptop, CPU). User asked to diagnose the cause model and do every CPU-side fix, then
              hand the GPU part to Krish. K2 still FAILs, now by less: 11-19 complete-data fine-tune top-1 0.209 vs
              floor 0.254 (−4.5 pp); post-hoc recalibration on calib prints → 0.294 (+4.1 pp, need > +5), ECE 0.26 →
              0.05. Label audit: z_offset_low is 98 % README-flagged bad values; 17.5 % of frames sit in CAXTON's
              post-change gap. v2 training recipe + clean labels built and CPU-tested; GPU sitting written.
NEXT ACTION:  1. Krish: docs/gpu-runs/SITTING-2026-11-21.md (block A screens 3 recipes on folds 0/1 by calib
                 cross-fit; B = winner on folds 2–4 + evals; C = runtime final.pt + T-only calibration + qhat).
              2. When A/B land: `git pull`, read reports/recalibration_v2_*.md and cause_eval_v2*.md. If K2 still
                 fires on the v2 model, user decides: pivot (ADR-0002 option 1) or DESCEND (see questions).
              3. If v2 wins: point config/default.yaml at models/cause/v2/<w>/final.pt + its recal_t files (needs D9).
DEMO:         config/caxton_demo.yaml now uses T-only calibration (models/cause/recal_t) and Grad-CAM.

## Load for next session
- project-context/STATE.md (this file)
- project-context/11-tickets/SEQUENCE.md, BOARD.md (status column)
- reports/label_experiments.md (the 11-21 numbers), docs/gpu-runs/SITTING-2026-11-21.md
Nothing else.

## Scope (ADR-0009, accepted; Dr. Meti signed off 2026-10-27)
- Ours: cause model (causability), explanation (CAM on the cause backbone, conformal set, counterfactual
  proposal), proactive early warning, 4-layer gate, HITL loop + dashboard + study, offline evaluation, hand-off doc.
- Not ours: printer connection, OctoPrint/G-code transport testing, camera/Pi choice, rig runs, envelope sign-off
  for a real printer, detector training. The `Printer` protocol is the boundary (docs/HANDOFF.md).
- All heavy compute runs on the teammate's GPU laptop (runbooks in docs/gpu-runs/). The public label CSV and small
  image subsets can be fetched on the dev laptop (D:\caxton; scripts/fetch_caxton_subset.py).

## Built (main)
- Core: types (SCHEMA_VERSION 2, CAXTON CAUSES, MANUAL_ADVICE, EARLY_WARNING, CauseWarning), config (+ proactive,
  use_defect, nullable detector, optional cause_model.calibration, attribution.method), store
- Gate: L2 → L1 → L3 → L4 + event_verdict (row 7 manual causes, row 9 never APPLYs a warning)
- Explain: cause_model (9-way or 4-head checkpoints via `heads`, joint_to_causes, optional calibration
  softmax(log p / T + τ log π)), conformal, counterfactual, sensors, attribution (EigenCAM + Grad-CAM per cause),
  build_explainer, Explainer.estimate
- Loop: orchestrator (heatmap job gets the card's top cause), proactive.py (EWMA + hysteresis), camera, FakePrinter,
  detector optional, ui/ui_data, study, docs/HANDOFF.md + tests/test_printer_contract.py
- Scripts: adapt_caxton, build_crops, audit_data, derive_window, make_splits, eval_cause, train_cause (+ v2 flags:
  --heads 4, --lp-epochs, --lr-backbone, --aug safe, --loss plain, --ema, --train-rows), eval_conformal,
  eval_counterfactual, eval_proactive, eval_latency, acceptance, gate_audit, analyze_study, probe_features
  (+ --train-rows), run_demo, recalibrate (new), clean_labels (new)

## Results so far (cause model, 5 leave-prints-out folds)
| model | top-1 | floor | gap | balanced | ECE | set size |
|---|---|---|---|---|---|---|
| 11-19 fine-tune, raw | 0.209 | 0.254 | −4.5 | 0.177 | 0.26 | 7.10 |
| + T only (runtime demo) | 0.209 | 0.254 | −4.5 | 0.177 | 0.055 | 7.11 |
| + T + prior | 0.294 | 0.254 | +4.1 | 0.152 | 0.053 | 6.18 |
Downstream with honest probabilities: NFR-007 0 confident events, NFR-012 recall 0.00 (model is rarely sure).

## Waiting on teammate runs
| Sitting | Tickets | Send back |
|---|---|---|
| SITTING-2026-11-21 (A ≈ 3.5 h, B ≈ 1.75 h, C ≈ 45 min) | T-0013 v2 | per block, see the doc |
| SITTING-2026-11-16 leftovers | T-0038 retake, T-0043/44 human pilot, T-0067, T-0066 demo | see that doc |
Outdated, don't run: docs/gpu-runs/T-0030.md, SITTING-2026-11.md.
After everything: `uv run pytest --junitxml reports/pytest.xml` + `scripts/acceptance.py` closes T-0046. Then T-0047.

## Decisions settled (2026-10-27)
- ADR-0009 accepted; Q1–Q5 answered. Labels = CAXTON *_class columns (07 §15); z_offset causes manual.
- Split: 5-fold GroupKFold by print; calib = 20 % of training prints; θ_on chosen per fold on calib prints only.
- Early warnings never auto-applied; warning ESCALATE = card, no pause; applied warnings are not verifier-watched.
- K1′ rule (T-0006). T-0024 window: p1–p99 of good-class setpoints; config edited only after the user reads it.

## Settled — do not relitigate
- Implementation order = 11-tickets/SEQUENCE.md (63 steps). Changes need user approval + check_sequence OK.
- New standalone `xqi` package. ADR-0001 · Image-only cause model, no telemetry input. ADR-0002 (labels may use
  logged values; inputs may not)
- Split-conformal LAC, α = 0.10. ADR-0003 · Pure 4-layer gate, fail-closed. ADR-0004 · Streamlit + SQLite. ADR-0005
- Critical classes default to M112. ADR-0006 · Leave-parts-out eval frozen at T-0007. ADR-0007 (re-scoped)
- Software-only scope with CAXTON. ADR-0009 · 07 §11 EigenCAM orients v₁ by Σ(A v₁)
- Tooling: uv + hatchling, Python 3.11, torch cu126 index, pytest skips gpu/hw/slow, ruff excludes .claude.
- Cause checkpoints go through save_checkpoint; plain state dicts are refused. Recalibration is fitted on calib prints
  only; a runtime calibration file and its qhat must come from the same recalibrate output.

## Questions for the human (recommended answer in brackets)
- D7 K2 test set: judge on data/crops_clean.csv (drops README-flagged z and the CAXTON gap)? [yes; report both]
- D8 K2 metric: top-1 vs majority floor rewards predicting z_offset_high (a manual cause). Add balanced accuracy as
  co-primary (the build plan's rule)? [yes, co-primary; top-1 kept for continuity]
- D9 Runtime: adopt T-only calibration + Grad-CAM in default.yaml (07 §8/§11 text)? [yes, already in the demo config]
- D10 z_offset_low cannot be learned from CAXTON (7 clean images). Keep it as a cause with manual advice only? [yes]
- D6: 06 vs 07 §7 NFR-002/003 [07 §7]. 09 §Data adapt_counts.json [yes]. Q2 GPU sittings owner [Krish].

## Highest unretired risk
K2: the v2 recipe on clean labels (SITTING-2026-11-21) is the last cheap lever before the pivot decision. CAXTON's
84.3 % is a random-image split; no held-out-print bar exists. Second: domain gap to the integrating team's camera
(T-0067). Runtime crop mismatch: training = 320 px nozzle box; live defect path = detector box + 20 % pad.

## Kill criteria watch
- K1′ PASS · K2 FAIL (11-19 raw −4.5 pp; recalibrated +4.1 pp ≤ 5); v2 run pending, then the user's decision · K3 dropped
- Known test issues: test_cli_run_mode_overrides_config fails on CPU-only machines (default.yaml cuda:0 + final.pt);
  test_replay_fps_paces_playback flakes under heavy CPU load.
