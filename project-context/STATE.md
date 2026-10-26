# STATE — SDP: Explainable, safe HITL correction for FFF (CARR 4.1.3 slice)

PHASE:        5 — EXECUTE
LAST SESSION: 2026-10-26 — camera-roll audit (T-0002 item 2 partial) + parallel run 1: 16 of 24 unblocked CODE
              tickets merged (13 DONE, 3 WAITING-GPU), T-0018 BLOCKED-SPEC, 7 downstream tickets skipped.
NEXT ACTION:  User decides the T-0018 DESCEND (07 §11 sign rule). If approved: edit 07 §11, merge branch t0018,
              then parallel run 2 = T-0034 → T-0051 → {T-0036, T-0038, T-0052} → T-0043 → T-0044.
              T-0002 (HUMAN) is still open and still blocks the data lane (steps 27+).

## Load for next session
- project-context/STATE.md (this file)
- project-context/11-tickets/SEQUENCE.md, BOARD.md (status column)
- the next ticket's file + the sections its Context: line names
Nothing else.

## Built so far
- P1: xqi/types.py, xqi/config.py (load, load_causes), xqi/store.py
- Gate: xqi/gate.py: L2 → L1 → L3 + event_verdict (L4), round_half_up. tests/test_gate_property.py, scripts/gate_audit.py,
  reports/recipe_audit.md (T-0021/22/23)
- Explain: xqi/explain/ has cause_model.py (T-0011, build_model(..., pretrained=True)), conformal.py (T-0014; load_qhat
  returns {qhat, alpha, n}), counterfactual.py (T-0016; severity, make_proposal(..., defect_id=''), gcode),
  sensors.py (T-0019), and the Explainer in __init__.py (T-0020)
- Loop I/O: xqi/printer.py (Printer protocol, FakePrinter, OctoPrint client with mocked HTTP; T-0026/27),
  xqi/camera.py (camera + replay folder; T-0029), xqi/detect.py (YOLO wrapper + ConfirmationTracker; T-0030/31),
  xqi/verify.py (T-0035)
- Orchestrator: xqi/orchestrator.py + xqi/__main__.py (baseline mode, critical-first, timings, CLI incl. `ui`; T-0033)
- UI: xqi/ui.py, xqi/ui_data.py (live view, read-only; T-0037)
- Suite: 174 passed, 3 deselected (gpu/slow) in ~33 s; ruff clean

## Waiting on the GPU / long-run team (runbooks in docs/gpu-runs/)
- T-0023: 100k-case @slow gate property run. CPU only, under 2 min. Send back reports/gate_property.md
- T-0030: gpu detector test. Needs models/yolo/best.pt (T-0002). Batch with T-0008 (G1)
- T-0037: manual replay check + reports/img/ui_live.png. Needs best.pt

## Decisions pending (user)
- D1: T-0018 DESCEND. 07 §11 "if ΣH < 0 then H ← −H" is degenerate (Ā row-centred ⇒ ΣĀv₁ ≡ 0). Proposed:
  "if Σ(A v₁) < 0". Branch t0018 (c1b8ed4) implements it and is green. Blocks T-0034 and everything after it.
- D2: gate rounding. For a fractional setpoint, half-up rounding after the L2 clip can exceed step by 0.5
  (210.5 + 5 → S216). Never happens with integer setpoints. Options: leave it as is (document it), or step x2 back
  toward x when |x2 − x| > step. The second option changes test_rounding_pushes_over_l1_limit (235.5 + 5 would pass at
  240 instead of being rejected).

## Parallel-run setup (user request, 2026-10-26)
- Workflow script: builds each ticket in its own worktree (.claude/worktrees/, gitignored), test-first, with the main
  .venv (PYTHONPATH=. python -m pytest; never uv sync in a worktree), then one serial integrator merges, tests,
  updates BOARD/LOGBOOK, pushes, and comments runbooks on issues.
- No heavy compute on the dev laptop: default-marker unit tests + ruff only. Training/eval/bench/soak/gpu/hw runs go
  to the team via docs/gpu-runs/T-00NN.md (docs/GPU_SETUP.md).
- Agent worktrees for merged tickets can be removed (`git worktree remove`). Keep t0018's until D1 is decided.

## Settled — do not relitigate
- Implementation order = 11-tickets/SEQUENCE.md, 52 steps. Changes need user approval + scripts/check_sequence.py OK.
  Parallel runs keep dependency order.
- New standalone `xqi` package; REU code is reference only. ADR-0001
- Image-only learned cause model; telemetry is never a model input. ADR-0002
- Split-conformal LAC sets, α = 0.10. ADR-0003
- Pure 4-layer gate: L2 clips, L1/L3 reject, L4 routes; fail-closed. ADR-0004
- Streamlit + SQLite, two processes; UI only inserts operator_decisions. ADR-0005
- Critical classes default to M112 (deck parity). ADR-0006
- LOGO by trial is the frozen eval. ADR-0007 (frozen at T-0007)
- Non-goals: RL, firmware changes, new sensors, new DOE, generative counterfactuals (06-requirements §Non-goals)
- Tooling: uv + hatchling, Python 3.11, torch/torchvision from the pytorch-cu126 index, pytest addopts skip gpu/hw/slow,
  ruff excludes .claude

## Data (T-0002)
- Received 2026-10-26: Drive "Camera Roll" = 5,490 unlabelled 1280×720 stills of ONE print (2025-04-29). No labels,
  splits, log or weights. Useful later as a replay feed and a false-alarm set (all frames = one trial). See
  docs/inherited/camera_roll_report.html and HANDOVER.md. Questions are posted on #2.
- Still missing: the labelled 6,454-image YOLO export + splits, best.pt, the induction log, the REU loop code,
  OctoPrint details, the protocol doc. The photos show a dual-hotend toolhead, not the Ender 5 Plus: confirm the rig.

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
A1 [unknown]: can the REU induction log be joined to individual boxes (K1, at the T-0006 audit)? The hand-over so far
has no log at all. If it never arrives, the learned cause model falls back to ADR-0002.

## Kill criteria watch
- K1 at T-0006 · K2 at T-0013 · K3 at week 6 (T-0028 / T-0039)
