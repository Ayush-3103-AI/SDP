# STATE — SDP: Explainable, safe HITL correction for FFF (CARR 4.1.3 slice)

PHASE:        5 — EXECUTE
LAST SESSION: 2026-10-04 — reviewed the teammate's P1 (T-0003 contracts, T-0004 config, T-0032 store), all DONE.
              Fixed: store SCHEMA_VERSION now imported from types; detections.ts was always 0.0.
NEXT ACTION:  SEQUENCE.md step 6 = T-0021 (gate L1+L2). T-0002 (HUMAN) is still open and must be running.

## Load for next session
- project-context/STATE.md (this file)
- project-context/11-tickets/SEQUENCE.md (canonical order)
- project-context/11-tickets/T-0021.md
- the sections its Context: line names
Nothing else.

## Built so far (P1 done except T-0002)
- xqi/types.py: §Types dataclasses + §Constants defaults, SCHEMA_VERSION = 1
- xqi/config.py: load(path) -> frozen Config; ConfigError("<dotted.key>: <why>"); config/default.yaml, causes.yaml
- xqi/store.py: Store(path) WAL, busy_timeout 2000 ms; open_readonly + insert_decision for the UI;
  write_detection(det, ts) is batched (25) and flushed on close

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
- Tooling: uv + hatchling, Python pinned 3.11 (.python-version), torch/torchvision from the pytorch-cu126 index, pytest addopts skip gpu/hw/slow

## Open branches
- B1 cause taxonomy → T-0007
- B2 envelope numbers → T-0024 / T-0025
- B3 clog: estop vs pause → T-0025 (Dr. Meti)
- B4 leave-one-printer-out → T-0050 (COULD)
- B5 nothing loads config/causes.yaml at runtime (09 lists only config.load). Needs a loader + 09 entry (DESCEND)
  by T-0006/T-0007. Until then tests/test_config.py pins it equal to the types.py defaults.

## Questions for the human (answer at the gate; recommended answer in brackets)
- Q1 Semester end date / demo date? [assume ~14 weeks from 2026-10-05; the week plan in BOARD.md uses that]
- Q2 Team size and who is the HUMAN owner for T-0002, T-0025, T-0041, T-0045? [team lead owns 0002; two people for 0041]
- Q3 Any KLE SDP rubric or CARR lab standard to follow (doctrine hook)? [none → this framework governs]
- Q4 Does Dr. Meti accept the charter thresholds S1–S5? [accept as written; revisit at the T-0013 gate review]
- Q5 Teammates: please update BOARD.md / STATE.md / LOGBOOK.md in the same PR as the ticket (CLAUDE.md step 7).

## Highest unretired risk
A1 [unknown]: whether the REU induction log can be joined to individual boxes (K1, at the T-0006 audit).
If it fails, the learned cause model (the core of the explanation layer) is replaced by the ADR-0002 fallback.
T-0002 is the head of the critical path and is still open.

## Kill criteria watch
- K1 at T-0006 · K2 at T-0013 · K3 at week 6 (T-0028 / T-0039)

## Deferred questions raised out of phase
- C: drive has < 1 GB free, so `uv sync` fails unpacking CUDA torch into the default uv cache. Free space on C:
  or set UV_CACHE_DIR to a D: path permanently (this session used D:/uv-cache per command).
