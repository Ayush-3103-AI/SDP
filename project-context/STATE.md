# STATE — SDP: Explainable, safe HITL correction for FFF (CARR 4.1.3 slice)

PHASE:        4 — TICKET (Phases 0–3 compressed into one session; awaiting gate approval)
LAST SESSION: 2026-10-03 — wrote 00–10, ADR-0001..0007, 52 tickets + BOARD, CLAUDE.md
NEXT ACTION:  SEQUENCE.md step 1 = T-0002 (human: request the REU hand-over today). Step 2 = T-0001 (Claude Code).

## Load for next session
- project-context/STATE.md (this file)
- project-context/11-tickets/SEQUENCE.md (canonical order)
- project-context/11-tickets/T-0001.md
- project-context/09-interfaces.md §Repo layout
Nothing else.

## Settled — do not relitigate
- Implementation order = 11-tickets/SEQUENCE.md, 52 steps; changes need user approval + scripts/check_sequence.py OK
- New standalone `xqi` package; REU code is reference only — ADR-0001
- Image-only learned cause model; telemetry never a model input — ADR-0002 (one-way for eval validity)
- Split-conformal LAC sets, α = 0.10 — ADR-0003
- Pure 4-layer gate: L2 clips, L1/L3 reject, L4 routes; fail-closed — ADR-0004
- Streamlit + SQLite, two processes; UI only inserts operator_decisions — ADR-0005
- Critical classes default M112 (deck parity) — ADR-0006
- LOGO by trial is the frozen eval — ADR-0007 (frozen at T-0007)
- Non-goals: RL, firmware changes, new sensors, new DOE, generative counterfactuals — 06-requirements §Non-goals

## Open branches
- B1 cause taxonomy → T-0007
- B2 envelope numbers → T-0024 / T-0025
- B3 clog: estop vs pause → T-0025 (Dr. Meti)
- B4 leave-one-printer-out → T-0050 (COULD)

## Questions for the human (answer at the gate; recommended answer in brackets)
- Q1 Semester end date / demo date? [assume ~14 weeks from 2026-10-05; the week plan in BOARD.md uses that]
- Q2 Team size and who is the HUMAN owner for T-0002, T-0025, T-0041, T-0045? [team lead owns 0002; two people for 0041]
- Q3 Any KLE SDP rubric or CARR lab standard to follow (doctrine hook)? [none → this framework governs]
- Q4 Does Dr. Meti accept the charter thresholds S1–S5? [accept as written; revisit at the T-0013 gate review]

## Highest unretired risk
A1 [unknown]: whether the REU induction log can be joined to individual boxes (K1, at the T-0006 audit).
If it fails, the learned cause model (the core of the explanation layer) is replaced by the ADR-0002 fallback.
T-0002 must start on day 1; it is the head of the critical path.

## Kill criteria watch
- K1 at T-0006 · K2 at T-0013 · K3 at week 6 (T-0028 / T-0039)

## Deferred questions raised out of phase
- None yet.
