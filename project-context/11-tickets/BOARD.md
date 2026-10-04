<!-- HEAD
FILE:     11-tickets/BOARD.md
PHASE:    4 — TICKET
UPDATED:  2026-10-03
STATUS:   draft (awaiting gate)
SUMMARY:  52 tickets: 41 CODE, 7 PAIR, 4 HUMAN (including 3 COULD stretch tickets).
          The effort-weighted critical path (~44 working days) is the DATA lane:
          T-0002 → 0005 → 0006(K1) → 0007 → 0009 → 0012 → 0013(K2) → 0015 → 0039 → 0041 → 0045 → 0046 → 0047.
          The software lanes (gate, printer, loop, UI) need no data and are built while T-0002 is pending.
          Rule: whenever a data-lane ticket is unblocked, it preempts the others (risk first).
OPEN:     week plan assumes a ~14-week semester starting 2026-10-05 (STATE Q1).
-->

# Board

**GitHub:** issue #N = ticket T-000N at https://github.com/Ayush-3103-AI/SDP/issues. Milestones = PLAN-4W phases.

## Lanes
| Lane | Tickets | Needs |
|---|---|---|
| **critical-path (data → rig → report)** | 0002, 0005, 0006, 0007, 0009, 0012, 0013, 0015, 0039, 0041, 0045, 0046, 0047 | REU hand-over, GPU, printer |
| core (integration) | 0001, 0003, 0004, 0010, 0011, 0017, 0020, 0033, 0034, 0036, 0038, 0042, 0051 | — |
| parallel-A (printer, loop I/O) | 0008, 0026, 0027, 0028, 0029, 0030, 0031, 0032, 0035, 0052 | printer only for 0028 |
| parallel-B (safety gate, conformal, counterfactual) | 0014, 0016, 0019, 0021, 0022, 0023, 0024, 0025 | nothing (0024/0025 need trials.csv) |
| parallel-C (UI, study) | 0018, 0037, 0043, 0044 | — |
| parallel-D (campaign design) | 0040 | frozen taxonomy |
| stretch (COULD) | 0048, 0049, 0050 | only after 0046 |

## Dependency DAG (by level; a ticket can start once every ticket it depends on is done)
```
L1  0001[C] 0002[H]
L2  0003[C]
L3  0004[C] 0005[C] 0014[C] 0018[C] 0029[C] 0030[C] 0032[C]
L4  0006[C] 0008[C] 0011[C] 0016[C] 0019[C] 0021[C] 0024[C] 0026[C] 0035[C] 0037[C]
L5  0007[P] 0020[C] 0022[C] 0027[C] 0031[C] 0049[C]
L6  0009[C] 0023[C] 0028[P] 0033[C] 0040[C]
L7  0010[C] 0012[P] 0025[H] 0034[C]
L8  0013[P] 0036[C] 0051[C]
L9  0015[C] 0017[C] 0038[C] 0052[C] 0050[P]
L10 0039[P] 0043[C]
L11 0041[H] 0044[C]
L12 0042[C] 0045[H]
L13 0046[C] 0048[C]
L14 0047[P]
```
C = Claude Code; P = Claude + human; H = human only.

## Execution order
The one canonical order is **[SEQUENCE.md](SEQUENCE.md)** (52 steps, dependency-checked by `scripts/check_sequence.py`). Don't keep a second order here.

## Week plan (assumed: 14 weeks from 2026-10-05)
| Week | Target |
|---|---|
| 1 | 0002 started (human); 0001, 0003, 0004, 0021, 0022, 0014 |
| 2 | 0016, 0019, 0023, 0011, 0026, 0027, 0029, 0032, 0031 |
| 3 | 0035, 0030, 0018, 0020, 0033 · **data in hand** → 0005, 0006 (K1) |
| 4 | 0007, 0008, 0024, 0009, 0010, 0012 (first read on A3) |
| 5 | 0013 (K2), 0034, 0051 |
| 6 | 0015, 0017, 0052, 0037, 0025 sign-off, 0028 · **K3: rig working?** |
| 7 | 0038, 0036, 0040, 0043 |
| 8 | 0039 dry run |
| 9–11 | 0041 campaign (0044 in parallel) |
| 12 | 0042, 0045 study |
| 13 | 0046 |
| 13–14 | 0047 report |

## Status
| Ticket | Owner | Pri | Status |
|---|---|---|---|
| T-0001 Scaffold repo | C | MUST | DONE |
| T-0002 Inheritance package | H | MUST | TODO |
| T-0003 Contracts module | C | MUST | DONE |
| T-0004 Config loader | C | MUST | DONE |
| T-0005 Induction adapter | C | MUST | BLOCKED (0002) |
| T-0006 Data audit + K1 | C | MUST | BLOCKED |
| T-0007 Freeze taxonomy + splits | P | MUST | BLOCKED |
| T-0008 Detector baseline | C | MUST | BLOCKED |
| T-0009 Crop dataset | C | MUST | BLOCKED |
| T-0010 Eval harness + floor | C | MUST | BLOCKED |
| T-0011 Cause model | C | MUST | TODO |
| T-0012 Train fold 0 | P | MUST | BLOCKED |
| T-0013 LOGO CV + K2 | P | MUST | BLOCKED |
| T-0014 Conformal | C | MUST | TODO |
| T-0015 Conformal eval | C | MUST | BLOCKED |
| T-0016 Proposals/counterfactual | C | MUST | TODO |
| T-0017 CF fidelity eval | C | MUST | BLOCKED |
| T-0018 EigenCAM | C | SHOULD | TODO |
| T-0019 Sensor checks | C | MUST | TODO |
| T-0020 Explainer | C | MUST | TODO |
| T-0021 Gate L1+L2 | C | MUST | TODO |
| T-0022 Gate L3+verdict | C | MUST | TODO |
| T-0023 Gate property + recipe audit | C | MUST | TODO |
| T-0024 Derive L3 window | C | MUST | BLOCKED |
| T-0025 Envelope sign-off | H | MUST | BLOCKED |
| T-0026 Printer + FakePrinter | C | MUST | TODO |
| T-0027 OctoPrint client | C | MUST | TODO |
| T-0028 OctoPrint smoke | P | MUST | BLOCKED |
| T-0029 Frame sources | C | MUST | TODO |
| T-0030 Detector wrapper | C | MUST | TODO |
| T-0031 Confirmation tracker | C | MUST | TODO |
| T-0032 Event store | C | MUST | DONE |
| T-0033 Orchestrator baseline | C | MUST | TODO |
| T-0034 Orchestrator modes | C | MUST | TODO |
| T-0035 Outcome verifier | C | MUST | TODO |
| T-0036 Latency report | C | MUST | TODO |
| T-0037 Dashboard live view | C | MUST | TODO |
| T-0038 Proposal cards | C | MUST | TODO |
| T-0039 HIL dry run | P | MUST | BLOCKED |
| T-0040 Campaign protocol | C | MUST | BLOCKED |
| T-0041 Run campaign | H | MUST | BLOCKED |
| T-0042 Rig results | C | MUST | BLOCKED |
| T-0043 Study mode | C | SHOULD | TODO |
| T-0044 Study analysis | C | SHOULD | TODO |
| T-0045 Run study | H | SHOULD | BLOCKED |
| T-0046 Acceptance report | C | MUST | BLOCKED |
| T-0047 Report/paper | P | MUST | BLOCKED |
| T-0048 Recalibrate (COULD) | C | COULD | TODO |
| T-0049 Tiled inference (COULD) | C | COULD | BLOCKED |
| T-0050 Leave-one-printer-out (COULD) | P | COULD | BLOCKED |
| T-0051 Operator decisions + timeouts | C | MUST | TODO |
| T-0052 Soak test | C | MUST | TODO |

Statuses: TODO / BLOCKED (waiting on a dependency) / DOING / DONE / FAILED (a kill criterion fired → DESCEND).
