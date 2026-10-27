# STATE — SDP: Explainable, safe HITL correction for FFF (CARR 4.1.3 slice)

PHASE:        DESCEND → 0/1 (re-charter) — gate pending. Phase 5 execution of the data lane is paused.
LAST SESSION: 2026-10-27 — the camera roll is the ENTIRE REU hand-over (K1 fired). User directive: SOFTWARE ONLY
              (model, causability, explainability, proactive HITL). Hardware, printer link, protocol and Pi/camera
              belong to another team. Wrote ADR-0009 (proposed; supersedes ADR-0008) + charter Amendment 2
              (proposed). Cause data = public Cambridge CAXTON set (~1.27 M images, 192 parts, parameter labels).
NEXT ACTION:  GATE: user approves / revises ADR-0009 and answers its Q1–Q5 (public data OK, detector pluggable,
              meaning of "proactive", hand-off contents, Dr. Meti). Then, in fresh sessions:
              1. Phase 2 delta: edit 06–09 per ADR-0009 (cause labels from CAXTON bins, proactive-warning FR + math,
                 leave-parts-out, hand-off API; fold in D2–D5 below).
              2. Phase 4 delta: drop the rig tickets, rewrite the data-lane tickets, add proactive + hand-off tickets,
                 re-order SEQUENCE (check_sequence.py OK).
              3. Execute: the CAXTON subset download + preprocessing runbook (GPU laptop) and the CAXTON adapter (CODE).
              Still useful now: the no-GPU runbooks T-0023, T-0052, T-0037/38, T-0043/44.

## Load for next session
- project-context/STATE.md (this file)
- project-context/11-tickets/SEQUENCE.md, BOARD.md (status column)
- the next ticket's file + the sections its Context: line names
Nothing else.

## Built so far (main 83ba73c: 208 passed, 5 deselected in ~90 s; ruff clean)
- P1: xqi/types.py, xqi/config.py (load, load_causes), xqi/store.py
- Gate: xqi/gate.py (L2 → L1 → L3, event_verdict/L4, round_half_up), tests/test_gate_property.py, scripts/gate_audit.py,
  reports/recipe_audit.md
- Explain: xqi/explain/ has cause_model.py, conformal.py (load_qhat → {qhat, alpha, n}), counterfactual.py (severity,
  make_proposal(..., defect_id=''), gcode), sensors.py, attribution.py (EigenCAM, 07 §11 as amended), and the
  Explainer in __init__.py
- Loop I/O: xqi/printer.py (Printer, FakePrinter, OctoPrint client), xqi/camera.py, xqi/detect.py (YOLO wrapper +
  ConfirmationTracker), xqi/verify.py
- Orchestrator: xqi/orchestrator.py: baseline, critical-first, gated-recipe/auto/advisory, operator decisions +
  timeouts. xqi/__main__.py: run / ui / study
- UI + study: xqi/ui.py, xqi/ui_data.py (live view, proposal cards), xqi/study.py, docs/study_protocol.md,
  scripts/analyze_study.py
- Bench/soak: scripts/eval_latency.py (--selftest ok), tests/test_soak.py (@slow), tests/conftest.py (FastClock,
  StubDetector)

## Waiting on team runs (runbooks: docs/gpu-runs/T-00NN.md; manual: docs/GPU_SETUP.md)
| Ticket | Needs | Time | Send back |
|---|---|---|---|
| T-0023 | CPU only, `-m slow` | < 2 min | reports/gate_property.md |
| T-0052 | CPU only, soak `-m slow` | 10–20 min | reports/soak_T-0052.txt |
| T-0037 | Streamlit + replay | ~15 min | reports/img/ui_live.png |
| T-0038 | Streamlit + stub loop (same sitting as 0037) | ~15 min | reports/img/ui_card.png |
| T-0043 | human pilot on Streamlit | ~40 min | reports/study/pilot.sqlite, reports/img/study_{off,on}.png |
| T-0044 | pilot.sqlite from T-0043 | ~2 min | reports/operator_study.md |
| T-0030 | GPU + best.pt (G1 with T-0008) | ~2 min | issue comment output |
| T-0036 | GPU + best.pt, `--bench` | ~5 min, ~1.5 GB | reports/latency.md |
The T-0018 gpu test (test_real_best_pt_heatmap_fast) also runs in G1. When results are pushed: git pull, verify
Done-when, close the ticket (CLAUDE.md GPU step 6).

## Decisions pending (user; recommended answer in brackets)
- D2 gate rounding: for a fractional setpoint, half-up after the L2 clip can exceed step by 0.5 (210.5 + 5 → S216).
  Never happens with integer setpoints. [document it, no code change]
- D3 09 §Store says the loop only sets `consumed` on operator_decisions. FR-019 and the T-0051 code also insert
  choice=timeout rows (consumed=1). [approve a one-line DESCEND to 09]
- D4 xqi/__main__.py builds Orchestrator(explainer=None), so a real `xqi run` in auto/advisory ESCALATEs every
  non-critical defect and shows no proposal cards. No ticket owns this wiring. [wire the Explainer in __main__ now
  with a fallback when models/cause/final.pt or qhat.json is missing; real weights after T-0015]
- D5 the orchestrator never writes defects.crop_path, so study cards from real campaign runs have no image. This
  must be fixed before T-0041/T-0045. [fold into D4's wiring change, or into T-0039]

## Parallel-run setup (user request, 2026-10-26)
- Workflow script (session dir): each ticket in its own worktree (.claude/worktrees/, gitignored), test-first, with
  the main .venv (PYTHONPATH=. python -m pytest; never uv sync in a worktree, never edit pyproject/uv.lock). One
  serial integrator then merges, tests, updates BOARD/LOGBOOK, pushes, and comments runbooks on issues. Keeps
  SEQUENCE dependency order; overrides one-ticket-per-session at the user's request.
- No heavy compute on the dev laptop: default-marker unit tests + ruff only. Everything else goes through runbooks.
- psutil is used by the soak test and comes in through ultralytics. Declare it in the dev group at the next
  deliberate `uv lock`.

## Settled — do not relitigate
- Implementation order = 11-tickets/SEQUENCE.md, 52 steps. Changes need user approval + scripts/check_sequence.py OK.
- New standalone `xqi` package; REU code is reference only. ADR-0001
- Image-only learned cause model; telemetry is never a model input. ADR-0002
- Split-conformal LAC sets, α = 0.10. ADR-0003
- Pure 4-layer gate: L2 clips, L1/L3 reject, L4 routes; fail-closed. ADR-0004
- Streamlit + SQLite, two processes; UI only inserts operator_decisions. ADR-0005
- Critical classes default to M112 (deck parity). ADR-0006
- LOGO by trial is the frozen eval. ADR-0007 (frozen at T-0007)
- 07 §11 EigenCAM orients v₁ by Σ(A v₁) (DESCEND 2026-10-26, user-approved)
- Non-goals: RL, firmware changes, new sensors, new DOE, generative counterfactuals (06-requirements §Non-goals)
- Tooling: uv + hatchling, Python 3.11, torch/torchvision from the pytorch-cu126 index, pytest addopts skip gpu/hw/slow,
  ruff excludes .claude

## Data (T-0002)
- Received 2026-10-26: Drive "Camera Roll" = 5,490 unlabelled 1280×720 stills of ONE print (2025-04-29). No labels,
  splits, log or weights. Useful later as a replay feed and a false-alarm set (all frames = one trial). See
  docs/inherited/camera_roll_report.html and HANDOVER.md. Questions are posted on #2.
- 2026-10-27: the user confirmed this is ALL the data. It matches the AM_VM paper's Aion 500 + webcam + YOLOv8 work,
  not the deck's dataset. Inherited models: AM_1 = YOLOv8n 1-class `defect` detector; AM_2 = YOLOv8 image
  classifier (OK/blobs/cracks/spaghetti/stringing/under-extrusion). Plan: ADR-0008 (own recorded induced-defect
  campaign → own labels → own YOLO11-S → K1/K2 re-run on own data).

## Open branches
- B1 cause taxonomy → T-0007
- B2 envelope numbers → T-0024 / T-0025
- B3 clog: estop vs pause → T-0025 (Dr. Meti)
- B4 leave-one-printer-out → T-0050 (COULD)

## Questions for the human (recommended answer in brackets)
- Q1 Semester end / demo date? [~14 weeks from 2026-10-05]
- Q2 Team size and HUMAN owners for T-0002, T-0025, T-0041, T-0045? [team lead owns 0002; two people for 0041]
- Q3 Any KLE SDP rubric or CARR lab standard to follow? [none → this framework governs]
- Q4 Does Dr. Meti accept the charter thresholds S1–S5? [accept; revisit at the T-0013 gate review]

## Highest unretired risk
K1′: CAXTON access and licence (dataset licence not yet confirmed; size is large, so a stratified subset goes on the
GPU laptop). Second: domain gap. CAXTON is a nozzle close-up; the integrating team's camera may be whole-bed, so the
cause model may need their data later. The report must state this.

## Kill criteria watch
- K1 at T-0006 · K2 at T-0013 · K3 at week 6 (T-0028 / T-0039)
