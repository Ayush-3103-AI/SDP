# STATE — SDP: Explainable, safe HITL correction for FFF (CARR 4.1.3 slice), software only

PHASE:        5 — EXECUTE (re-planned per ADR-0009; delta gate APPROVED 2026-10-27).
LAST SESSION: 2026-11-07 — Krish's 11-06 data sitting gave K1′: FAIL. Root cause: our adapter dropped every
              z_offset < 0.08 (in CAXTON = every good/low Z). DESCEND approved: drop only the ambiguous bands
              (−0.08, 0) and (0.04, 0.08); local CSV-only re-audit → K1′ PASS (181 prints, 79,515 images, 830–9,922
              single-cause images per cause). logo.json removed for the rebuild. T-0067 domain_shift.py built.
              main 337 passed, 1 skipped, 5 deselected; ruff clean.
NEXT ACTION:  1. Krish re-runs T-0065 Part 2 then the rest of docs/gpu-runs/SITTING-2026-11.md (incl. T-0067).
              2. When pushed: git pull, verify Done-when; K1′ (expect PASS) then K2 first; then close tickets.
              3. User: NFR-002/003 DESCEND (blocks T-0066), adapt_counts.json 09 line, l3_window review.
DEMO:         the ~2026-11-03 demo date has passed; fallback stays synthetic replay + random-init model.

## Load for next session
- project-context/STATE.md (this file)
- project-context/11-tickets/SEQUENCE.md, BOARD.md (status column)
- the next ticket's file + the sections its Context: line names
Nothing else.

## Scope (ADR-0009, accepted; Dr. Meti signed off 2026-10-27)
- Ours: cause model (causability), explanation (EigenCAM on the cause backbone, conformal set, counterfactual
  proposal), proactive early warning, 4-layer gate, HITL loop + dashboard + study, offline evaluation, hand-off doc.
- Not ours: printer connection, OctoPrint/G-code transport testing, camera/Pi choice, rig runs, envelope sign-off
  for a real printer, detector training. The `Printer` protocol is the boundary (docs/HANDOFF.md).
- All heavy compute AND the dataset download run on the teammate's GPU laptop (runbooks in docs/gpu-runs/).

## Built (main)
- Core: types (SCHEMA_VERSION 2, CAXTON CAUSES, MANUAL_ADVICE, EARLY_WARNING, CauseWarning), config (+ proactive,
  use_defect, nullable detector), store (write_defect upserts paths)
- Gate: L2 → L1 → L3 → L4 + event_verdict (row 7 manual causes, row 9 never APPLYs a warning)
- Explain: cause_model (no defect input, save_checkpoint {use_defect, state_dict, meta}, causes-order check,
  to_input), conformal, counterfactual, sensors, attribution (EigenCAM on backbone.layer4), build_explainer
  (no-model fallback), Explainer.estimate
- Loop: orchestrator (all modes, proactive tick every_n frames, warning cards, heatmaps on a cause-net copy),
  proactive.py (EWMA + hysteresis), camera (replay + `caxton:<crops.csv>#<trial>`), FakePrinter.set_process,
  detector optional, ui/ui_data (advice, warning p̄), study, docs/HANDOFF.md + tests/test_printer_contract.py
- Scripts: adapt_caxton, build_crops, audit_data (K1′), derive_window, make_splits, eval_cause (floor, K2),
  train_cause (AMP, OOM halving, golden fixture), eval_conformal, eval_counterfactual, eval_proactive,
  eval_latency (--bench), acceptance, gate_audit, analyze_study; config/caxton_demo.yaml

## Waiting on teammate runs (runbooks docs/gpu-runs/T-00NN.md; manual docs/GPU_SETUP.md)
| Sitting | Tickets | Needs | Send back |
|---|---|---|---|
| Sitting 2026-11 (docs/gpu-runs/SITTING-2026-11.md) | T-0065 Part 2 (subset fetch) → T-0012 → T-0013 (K2) → T-0015, T-0017, T-0063 → T-0036; CPU: T-0037, T-0038, T-0043 → T-0044; Drive camera roll download | nothing | see the sitting doc's send-back table |
| Later | T-0066 demo (after the DESCEND) | T-0013/15 | demo outputs |
Outdated, don't run: docs/gpu-runs/T-0030.md.
After everything: `uv run pytest --junitxml reports/pytest.xml` + `scripts/acceptance.py` closes T-0046 (dry run
today: 23 PASS · 0 FAIL · 15 NO DATA of 38). Then T-0047 report (PAIR, one chapter per session).

## Decisions settled (2026-10-27)
- ADR-0009 accepted; Q1–Q5 answered. Labels = CAXTON *_class columns (07 §15); z_offset causes manual.
- Split: 5-fold GroupKFold by print (hand-rolled, no sklearn); calib = 20 % of training prints; θ_on chosen per
  fold on calib prints only (T-0063).
- Early warnings never auto-applied; warning ESCALATE = card, no pause; applied warnings are not verifier-watched.
- K1′ rule (T-0006): licence filled AND ≥ 4 setpoint causes with ≥ 200 single-cause images in ≥ 5 prints.
- T-0024 window: p1–p99 of good-class setpoints; config edited only after the user reads reports/l3_window.md.

## Settled — do not relitigate
- Implementation order = 11-tickets/SEQUENCE.md (63 steps). Changes need user approval + check_sequence OK.
- New standalone `xqi` package. ADR-0001 · Image-only cause model, no telemetry input. ADR-0002
- Split-conformal LAC, α = 0.10. ADR-0003 · Pure 4-layer gate, fail-closed. ADR-0004 · Streamlit + SQLite. ADR-0005
- Critical classes default to M112. ADR-0006 · Leave-parts-out eval frozen at T-0007. ADR-0007 (re-scoped)
- Software-only scope with CAXTON. ADR-0009 (supersedes ADR-0008) · 07 §11 EigenCAM orients v₁ by Σ(A v₁)
- Tooling: uv + hatchling, Python 3.11, torch cu126 index, pytest skips gpu/hw/slow, ruff excludes .claude.
  In agent worktrees run the main checkout's .venv python (uv run would create a venv + download CUDA torch).
- Cause checkpoints go through save_checkpoint; plain state dicts are refused.
- psutil (soak test) comes via ultralytics; declare it in the dev group at the next deliberate `uv lock`.

## Questions for the human (recommended answer in brackets)
- DESCEND D6: 06 vs 07 §7 disagree on NFR-002/003. [07 §7: NFR-002 = t_gate − t0 (frame → verdict), t_disp =
  send_gcode returned True; NFR-003 = event → card, with a recorded UI first-render ts in 09 §Store]
- 09 §Data: list data/adapt_counts.json (adapter exclusion counts read by audit_data). [yes, additive]
- Optional: add calib_cls to the preds npz (09 §Data + train_cause) so eval_proactive needn't join crops.csv. [later]
- Q2 Who owns T-0065 and the GPU sittings? [the teammate with the RTX 3050 laptop]

## Highest unretired risk
K1′ on the real audit (image location solved 2026-10-30; the subset fetch is untested at full scale: ~91 k range
requests). Then K2 at T-0013. Second: domain gap (nozzle close-up vs the integrating team's camera); T-0067 measures it
on the Drive camera roll. Krish's GPU is an RTX 4050, not the spec's 3050: S4 must name the GPU.

## Kill criteria watch
- K1′ at T-0006 (real audit from T-0065) · K2 at T-0013 · K3 dropped
