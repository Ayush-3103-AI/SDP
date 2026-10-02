<!-- HEAD
FILE:     11-tickets/PLAN-4W.md
PHASE:    5 — EXECUTE (implementation plan)
UPDATED:  2026-10-03
STATUS:   draft
SUMMARY:  Implementation-only plan: 7 phases over 4 weeks (20 working days), 42 tickets.
          The 2-week cut line is the full software loop running end-to-end on replay frames + FakePrinter
          with a stub cause model. Weeks 3–4 add the real data/model and the rig integration.
          Out of scope here: the induced-defect campaign, the operator study, the report, and COULD tickets.
OPEN:     Phase 4 needs the REU hand-over (T-0002) in hand by Day 6.
-->

# 4-Week Implementation Plan

## Phase 1 — Foundations (Days 1–2)
| Ticket | Output |
|---|---|
| T-0001 | repo, uv, pytest, ruff |
| T-0003 | `xqi/types.py` contracts |
| T-0004 | config loader + `default.yaml` / `causes.yaml` |
| T-0032 | SQLite event store |

**Exit:** `uv run pytest` is green; types, config and store round-trip.

## Phase 2 — Decision core: pure logic, no data needed (Days 3–5)
| Ticket | Output |
|---|---|
| T-0021 | gate L1 + L2 |
| T-0022 | gate L3 + event-verdict table |
| T-0014 | conformal calibrate / predict_set |
| T-0016 | proposals, Δ scaling, counterfactual text |
| T-0019 | sensor checks |
| T-0023 | 100k gate property test + recipe audit |
| T-0035 | outcome verifier |

**Exit:** zero violations in 100 000 cases; `reports/recipe_audit.md` exists.

## Phase 3 — Printer I/O and the baseline loop (Days 6–8)
| Ticket | Output |
|---|---|
| T-0026 | Printer protocol + FakePrinter |
| T-0027 | OctoPrint client (HTTP mocked) |
| T-0029 | camera / replay sources |
| T-0030 | YOLO11 detector wrapper |
| T-0031 | confirmation tracker + severity |
| T-0033 | orchestrator: baseline mode, critical-first, timings, CLI |

**Exit:** `python -m xqi run --mode baseline` runs on replay + FakePrinter and reproduces the deck's recipes and M112.

## Phase 4 — Explanation layer (Days 9–10, stub model)
| Ticket | Output |
|---|---|
| T-0011 | cause model (architecture, predict, train step) |
| T-0018 | EigenCAM |
| T-0020 | Explainer assembly |

**Exit:** the Explainer returns a cause set, flags and proposals from a stub model.

### ── 2-WEEK CUT LINE ──
**2-week version:** do P1–P3, then on Days 9–10 do only T-0020 (stub model) + T-0034 + T-0051 + T-0037/T-0038 in their minimal form. Result: the complete loop (detect → explain → gate → card → apply → outcome) running offline on replay + FakePrinter. Real data (P6) and the rig (P7) move to weeks 3–4.

## Phase 5 — Modes and the human-in-the-loop dashboard (Days 11–14)
| Ticket | Output |
|---|---|
| T-0034 | gated-recipe / auto / advisory paths |
| T-0051 | operator decisions, re-gating, timeouts |
| T-0037 | dashboard live view |
| T-0038 | proposal cards + buttons |
| T-0052 | 2-hour soak test |

**Exit:** in advisory mode on replay, a card appears, Apply dispatches a gated command to the FakePrinter, and the outcome is logged.

## Phase 6 — Real data and model (Days 11–17; runs alongside Phase 5 once the hand-over arrives)
| Ticket | Output |
|---|---|
| T-0005 | induction-log adapter |
| T-0006 | data audit → **K1** |
| T-0007 | freeze taxonomy + LOGO splits |
| T-0008 | detector baseline reproduced |
| T-0009 | crop dataset |
| T-0010 | eval harness + floor |
| T-0012 | train fold 0 |
| T-0013 | full LOGO + final model → **K2** |
| T-0015 | conformal eval + `qhat.json` |
| T-0017 | counterfactual fidelity |
| T-0024 | derived L3 window |

**Exit:** `models/cause/final.pt` and `qhat.json` exist; cause, conformal and counterfactual reports are written; K1 and K2 are decided.

## Phase 7 — Rig integration (Days 18–20)
| Ticket | Output |
|---|---|
| T-0025 | envelope sign-off (human, 30 min) |
| T-0028 | OctoPrint smoke + dispatch latency |
| T-0036 | latency + VRAM report |
| T-0039 | dry run on the Ender 5 Plus (advisory + auto) |
| T-0040 | campaign matrix script |
| T-0042 | rig-results eval script (`--selftest`) |

**Exit:** the real model runs on the real printer with 0 violations; latency is measured against 0.30 s.

## Calendar
| Week | Days | Phases |
|---|---|---|
| 1 | 1–5 | P1, P2 · **request the REU hand-over (T-0002) on Day 1** |
| 2 | 6–10 | P3, P4 → 2-week cut line |
| 3 | 11–15 | P5 + P6 in parallel |
| 4 | 16–20 | P6 finishes, P7 |
