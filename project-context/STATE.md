# STATE — SDP: Explainable, safe HITL correction for FFF (CARR 4.1.3 slice), software only

PHASE:        5 — EXECUTE (re-planned; delta gate APPROVED by the user 2026-10-27). Phase 2 + 3 + 4 deltas done at
              the user's request ("go with all your recommendations and create specs and tickets").
LAST SESSION: 2026-10-27 — T-0057 DONE: CAXTON taxonomy in code (causes.yaml, MANUAL_ADVICE, EARLY_WARNING,
              SCHEMA_VERSION 2, use_defect=false cause model with checkpoint check, gate row 7 = manual causes,
              card advice). 221 passed; ruff clean.
NEXT ACTION:  Parallel run 3 (user-requested 2026-10-27): every CODE ticket that needs no teammate result.
              Step 30 T-0005 (CAXTON adapter, CODE). Then 31 T-0009 … per SEQUENCE.md Part B.
              Parallel option: BOARD lists the unblocked CODE set (0060, 0005, 0058, 0059 → …).
              Teammates now: T-0065 Part 1 + the CPU runs (T-0023, T-0052, T-0037/38, T-0043/44).

## Load for next session
- project-context/STATE.md (this file)
- project-context/11-tickets/SEQUENCE.md, BOARD.md (status column)
- the next ticket's file + the sections its Context: line names
Nothing else.

## Scope (ADR-0009, accepted)
- Ours: cause model (causability), explanation (EigenCAM on the cause backbone, conformal set, counterfactual
  proposal), proactive early warning, 4-layer gate, HITL loop + dashboard + study, offline evaluation, hand-off doc.
- Not ours: printer connection, OctoPrint/G-code transport testing, camera/Pi choice, rig runs, envelope sign-off
  for a real printer, detector training. The `Printer` protocol is the boundary (docs/HANDOFF.md, T-0064).
- All heavy compute AND the dataset download run on the teammate's GPU laptop (runbooks in docs/gpu-runs/).

## Built so far (main, T-0057; 221 passed, 5 deselected; ruff clean)
- P1: xqi/types.py, xqi/config.py, xqi/store.py
- Gate: xqi/gate.py (L2 → L1 → L3, event_verdict/L4), property test, scripts/gate_audit.py, reports/recipe_audit.md
- Explain: xqi/explain/ cause_model, conformal, counterfactual, sensors, attribution (YOLO path), Explainer
- Loop I/O: printer.py (Printer, FakePrinter, OctoPrint client = unsupported reference), camera.py, detect.py, verify.py
- Orchestrator (all modes, operator decisions, timeouts), __main__ (run / ui / study), ui.py, ui_data.py, study.py,
  scripts/analyze_study.py, scripts/eval_latency.py, tests/test_soak.py (@slow)

## What changes in code (by ticket)
| Ticket | Change |
|---|---|
| T-0057 ✔ | CAXTON CAUSES in causes.yaml, MANUAL_ADVICE, use_defect=false, verdict row 7 = manual causes, SCHEMA_VERSION 2 |
| T-0058 | build_explainer in `xqi run` (fallback when no model), Explainer.estimate, defects.crop_path (old D4, D5) |
| T-0059 | EigenCAM on the cause model's backbone.layer4 |
| T-0060/61 | xqi/proactive.py (EWMA + hysteresis, 07 §13); early-warning events in the loop, never auto-APPLY; detector optional |
| T-0062 | `caxton:<crops.csv>#<trial>` source + FakePrinter.set_process |
| T-0064 | docs/HANDOFF.md + tests/test_printer_contract.py |
| T-0005/09/06/24/07 | adapt_caxton, build_crops, audit_data (K1′), derive_window, make_splits |
| T-0010/12/13 | eval_cause (+ floor, CIs), train_cause (G2/G3 on the teammate laptop) |
| T-0015/17/63/36 | conformal, CF fidelity (confident events), proactive eval, latency bench |

## Waiting on team runs (runbooks: docs/gpu-runs/T-00NN.md; manual: docs/GPU_SETUP.md)
| Ticket | Needs | Time | Send back |
|---|---|---|---|
| T-0065 Part 1 | network, ~150 GB disk | 1 h + download | docs/data/CAXTON.md + CSV header in #65 |
| T-0023 | CPU, `-m slow` | < 2 min | reports/gate_property.md |
| T-0052 | CPU soak `-m slow` | 10–20 min | reports/soak_T-0052.txt |
| T-0037 / T-0038 | Streamlit + replay / stub loop | ~30 min | reports/img/ui_live.png, ui_card.png |
| T-0043 → T-0044 | human pilot, then analysis | ~45 min | pilot.sqlite, study pngs, reports/operator_study.md |
Outdated, don't run: docs/gpu-runs/T-0030.md, T-0036.md (banners added).

## Decisions settled this session (2026-10-27)
- ADR-0009 accepted; Q1–Q4 as recommended (public data OK, detector pluggable, proactive = warn + propose before a
  defect is confirmed with human approval, hand-off = xqi + Printer protocol + HANDOFF.md + FakePrinter).
- D2 gate rounding: documented in 07 §3, no code change. D3: 09 §Store now says the loop inserts timeout rows.
  D4/D5 → T-0058.
- Labels: CAXTON's own *_class columns (0/1/2 = low/good/high); single-deviation images train the model, `multi`
  images are kept for the proactive eval and replay (07 §15). z_offset causes are manual (advice, ESCALATE).
- Split: 5-fold GroupKFold by print; calib = 20 % of training prints; logo.json filename kept (hard rule still applies).
- Early warnings are never auto-applied (FR-030).

## Settled — do not relitigate
- Implementation order = 11-tickets/SEQUENCE.md (63 steps). Changes need user approval + check_sequence OK.
- New standalone `xqi` package. ADR-0001 · Image-only cause model, no telemetry input. ADR-0002
- Split-conformal LAC, α = 0.10. ADR-0003 · Pure 4-layer gate, fail-closed. ADR-0004 · Streamlit + SQLite. ADR-0005
- Critical classes default to M112. ADR-0006 · Leave-parts-out eval frozen at T-0007. ADR-0007 (re-scoped)
- Software-only scope with CAXTON. ADR-0009 (supersedes ADR-0008)
- 07 §11 EigenCAM orients v₁ by Σ(A v₁) (2026-10-26)
- Tooling: uv + hatchling, Python 3.11, torch cu126 index, pytest skips gpu/hw/slow, ruff excludes .claude
- Cause checkpoints are {use_defect, state_dict} (xqi.explain.cause_model.save_checkpoint); plain state dicts
  are refused. T-0012/13 training must save through it.
- psutil (soak test) comes via ultralytics; declare it in the dev group at the next deliberate `uv lock`.

## Questions for the human (recommended answer in brackets)
- Q2 Who on the team owns T-0065 (download) and the GPU sittings? [the teammate with the RTX 3050 laptop]
- Answered 2026-10-27: Q5 Dr. Meti signed off ADR-0009 (CAXTON, leave-parts-out, S5 thresholds).
  Q1 demo is NEXT WEEK (~2026-11-03), not mid-January: T-0065 download is now urgent; the demo falls back to
  synthetic replay + random-init/no-model path if CAXTON or the trained model is not ready.

## Highest unretired risk
K1′: the CAXTON image archive's download location is unverified (the Apollo record lists only the label CSVs,
CC BY 4.0). T-0065 Part 1 finds it or emails the authors. Fallback after 1 week: the Kaggle under-extrusion set
(binary) + priors, with S1 re-scoped (ADR-0009). Second: domain gap (nozzle close-up vs the integrating team's camera).

## Kill criteria watch
- K1′ at T-0006 (real audit from T-0065) · K2 at T-0013 · K3 dropped
