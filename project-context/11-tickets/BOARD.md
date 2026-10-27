<!-- HEAD
FILE:     11-tickets/BOARD.md
PHASE:    4 — TICKET (delta 2026-10-27, ADR-0009 software-only)
UPDATED:  2026-10-27
STATUS:   accepted delta
SUMMARY:  63 tickets: 22 DONE, 6 waiting on teammate CPU runs, 9 DROPPED (hardware/detector → integrating team),
          26 in the new plan (11 new: T-0057…T-0067). Critical path is the DATA lane:
          T-0057 → 0005 → 0006/0009/0024 → 0007 → 0065 (teammate download + data sitting) → 0012 (G2) → 0013 (G3, K2)
          → 0015/0017/0063 → 0066 (G4 demo) → 0046 → 0047. The proactive + hand-off lane (0058–0062, 0064) needs no data
          and is built while the teammate downloads.
OPEN:     T-0065 Part 1 (image location) is the highest risk (K1′).
-->

# Board

**GitHub:** issue #N = ticket T-000N at https://github.com/Ayush-3103-AI/SDP/issues (#53–56 are PRs, so the new tickets
start at T-0057 = #57).

## Lanes
| Lane | Tickets (open) | Needs |
|---|---|---|
| **critical-path (data → model → evals → demo → report)** | 0057, 0005, 0009, 0006, 0024, 0007, 0065, 0010, 0012, 0013, 0015, 0063, 0066, 0046, 0047 | teammate laptop for 0065, 0012, 0013, 0066 |
| proactive + loop | 0058, 0060, 0061, 0062 | nothing (fixtures) |
| explain | 0059, 0017 | nothing until T-0013 preds |
| hand-off | 0064 | nothing |
| bench | 0036 | GPU (G4) |
| study | 0043, 0044 (waiting), 0045 | humans |
| stretch (COULD) | 0048, 0067 | after 0066 / 0013 |

## Execution order
The one canonical order is **[SEQUENCE.md](SEQUENCE.md)** (dependency-checked by `scripts/check_sequence.py`). Its
"Teammate sittings" table says what the GPU laptop runs and when.

## Parallel build (when the user asks for a parallel run)
Unblocked CODE tickets right now, by DAG level (each can start once the tickets it lists are DONE):
```
L0  0057  0060
L1  0005 (0057)   0058 (0057)   0059 (0057)
L2  0009 (0005)   0006 (0005)   0024 (0005)   0061 (0058, 0060)
L3  0007 (0006)   0062 (0009)   0064 (0061)   0010 (0007, 0009)
then build-ahead (SEQUENCE rule 7): 0015, 0017, 0063, 0036 on synthetic fixtures
```

## Status
| Ticket | Owner | Pri | Status |
|---|---|---|---|
| T-0001 Scaffold the repo (git, uv project, package, test runner) | C | MUST | DONE |
| T-0002 Collect the inheritance package from the REU team | H | MUST | DONE |
| T-0003 Implement the contracts module (dataclasses, constants, JSON round-trip) | C | MUST | DONE |
| T-0004 Implement the config loader with validation, plus default.yaml and causes.yaml | C | MUST | DONE |
| T-0005 Write the CAXTON adapter (canonical trials.csv / images.csv, label rule, part-stratified subset) | C | MUST | DONE |
| T-0006 Write the data audit report (cause coverage per print, single-deviation share, kill check K1′) | C | MUST | WAITING-DATA (T-0065: K1′ on the real audit) |
| T-0007 Freeze the cause taxonomy and the leave-parts-out splits | P | MUST | WAITING-DATA (T-0065 step 5 writes logo.json; causes.yaml edit after approval) |
| T-0008 Reproduce the detector baseline on the REU split | C | MUST | DROPPED |
| T-0009 Build the nozzle-ROI crop dataset from images.csv | C | MUST | DONE |
| T-0010 Build the cause evaluation harness and the majority floor | C | MUST | TODO |
| T-0011 Implement the cause model (architecture, predict, training step) | C | MUST | DONE |
| T-0012 Train the cause model on leave-parts-out fold 0 (early read on A3) | P | MUST | BLOCKED |
| T-0013 Run the full leave-parts-out cross-validation and the K2 kill check | P | MUST | BLOCKED |
| T-0014 Implement split-conformal calibration and prediction sets | C | MUST | DONE |
| T-0015 Evaluate conformal coverage on the leave-parts-out folds and save the runtime qhat | C | MUST | TODO |
| T-0016 Implement proposal and counterfactual generation (severity-scaled Δ, G-code, sentence) | C | MUST | DONE |
| T-0017 Evaluate counterfactual direction fidelity on confident events | C | MUST | TODO |
| T-0018 Implement EigenCAM attribution on the YOLO11 backbone | C | SHOULD | DONE |
| T-0019 Implement the telemetry sensor checks | C | MUST | DONE |
| T-0020 Assemble the Explainer (cause model → conformal set → sensor flags → proposals) | C | MUST | DONE |
| T-0021 Implement safety gate layers L2 (rate/cooldown) and L1 (physical limits) | C | MUST | DONE |
| T-0022 Implement gate layer L3 and the event-verdict truth table (with L4) | C | MUST | DONE |
| T-0023 Write the randomised gate property test and the deck-recipe audit | C | MUST | WAITING-GPU (teammate CPU run) |
| T-0024 Derive the L3 process window from CAXTON's "good" class ranges | C | MUST | WAITING-DATA (T-0065: real window, then a config commit after user review) |
| T-0025 Confirm the envelope numbers and get sign-off | H | MUST | DROPPED |
| T-0026 Implement the Printer protocol and the FakePrinter simulator | C | MUST | DONE |
| T-0027 Implement the OctoPrint REST client | C | MUST | DONE |
| T-0028 Smoke-test OctoPrint on the real printer and measure dispatch latency | P | MUST | DROPPED |
| T-0029 Implement the frame sources (camera and replay folder) | C | MUST | DONE |
| T-0030 Implement the YOLO11 detector wrapper | C | MUST | DONE |
| T-0031 Implement the confirmation tracker (with severity) | C | MUST | DONE |
| T-0032 Implement the SQLite event store | C | MUST | DONE |
| T-0033 Implement the orchestrator: baseline mode, critical-first handling, timings, CLI | C | MUST | DONE |
| T-0034 Implement the orchestrator's gated-recipe, auto and advisory action paths | C | MUST | DONE |
| T-0035 Implement the outcome verifier | C | MUST | DONE |
| T-0036 Write the latency and VRAM report (offline bench) | C | MUST | TODO |
| T-0037 Build the dashboard live view (read-only) | C | MUST | WAITING-GPU (teammate CPU run) |
| T-0038 Build the dashboard proposal cards and operator buttons | C | MUST | WAITING-GPU (teammate CPU run) |
| T-0039 Hardware-in-the-loop dry run on the Ender 5 Plus (no induced defects) | P | MUST | DROPPED |
| T-0040 Write the induced-defect campaign protocol and the randomised run matrix | C | MUST | DROPPED |
| T-0041 Run the induced-defect campaign | H | MUST | DROPPED |
| T-0042 Evaluate the rig results (resolution, overshoot, violations, latency by mode) | C | MUST | DROPPED |
| T-0043 Build the operator-study mode (replay cards with explanation on/off) | C | SHOULD | WAITING-GPU (teammate CPU run) |
| T-0044 Write the operator-study analysis script | C | SHOULD | WAITING-GPU (teammate CPU run) |
| T-0045 Run the operator study sessions | H | SHOULD | BLOCKED |
| T-0046 Generate the acceptance report (every FR and NFR → PASS/FAIL with evidence) | C | MUST | BLOCKED |
| T-0047 Draft the SDP report and paper | P | MUST | BLOCKED |
| T-0048 (COULD) Recalibrate qhat from labelled logged events | C | COULD | TODO |
| T-0049 (COULD) Test tiled inference for under-extrusion | C | COULD | DROPPED |
| T-0050 (COULD) Evaluate the cause model leave-one-printer-out (Kobra 2 Neo) | P | COULD | DROPPED |
| T-0051 Implement operator-decision processing and timeouts in the loop | C | MUST | DONE |
| T-0052 Write the 2-hour soak test on replay + FakePrinter | C | MUST | WAITING-GPU (teammate CPU run) |
| T-0057 Adapt the explain stack to the CAXTON taxonomy (no defect input, manual z-offset causes, SCHEMA_VERSION 2) | C | MUST | DONE |
| T-0058 Wire the Explainer into `xqi run` (with a no-model fallback) and write defects.crop_path | C | MUST | TODO |
| T-0059 Run EigenCAM on the cause-model backbone | C | SHOULD | DOING (defect heatmaps done; warning heatmaps close with T-0061) |
| T-0060 Implement the early-warning module (EWMA + hysteresis) | C | MUST | TODO |
| T-0061 Add the proactive path to the loop (early-warning events, optional detector) | C | MUST | TODO |
| T-0062 Add the CAXTON replay source and process-seeded FakePrinter | C | MUST | TODO |
| T-0063 Evaluate proactive warnings on held-out prints (time-to-warning, recall, false-warning rate) | C | MUST | TODO |
| T-0064 Write the hand-off package (HANDOFF.md + Printer conformance test) | C | MUST | TODO |
| T-0065 Download CAXTON and run the data sitting on the teammate laptop | H | MUST | TODO |
| T-0066 Run the offline end-to-end HITL demo on held-out CAXTON prints | P | MUST | TODO |
| T-0067 (COULD) Check domain shift on the inherited camera roll | C | COULD | TODO |

Statuses: TODO / BLOCKED (waiting on a dependency) / DOING / WAITING-GPU or WAITING-DATA (built; waiting on a teammate
run) / DONE / FAILED (a kill criterion fired → DESCEND) / DROPPED (out of scope, ADR-0009).
