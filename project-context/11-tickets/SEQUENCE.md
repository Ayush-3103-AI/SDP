<!-- HEAD
FILE:     11-tickets/SEQUENCE.md
PHASE:    5 — EXECUTE (re-sequenced 2026-10-27 for ADR-0009, user-approved)
UPDATED:  2026-10-27
STATUS:   active — THE canonical implementation order
SUMMARY:  63 tickets, dependency-checked. Part A (steps 1–28) is built (DONE, or waiting on a teammate run).
          Part B (29–54) is the software-only plan: CAXTON data lane, proactive warning, hand-off, GPU
          sittings G2–G4 on the teammate laptop, demo, report. Part C (55–63) is dropped (hardware) and
          is kept only so the history and the checker stay whole. Next ticket = the first Part B step
          not DONE whose dependencies are DONE (rules 2 and 7).
OPEN:     none
-->

# Implementation sequence

## Rules
1. **The next ticket is the lowest-numbered step that isn't DONE (or DROPPED).** Don't reorder.
2. **Blocked on a human** (HUMAN/PAIR owner, or a dependency waiting on a teammate run): skip to the next step whose
   dependencies are all DONE, then come back as soon as it unblocks. Note every skip in LOGBOOK.md.
3. **HUMAN steps** are never executed by Claude Code. It tells the user what's needed and moves on per rule 2.
4. **A kill check** (K1′ at step 32 via 35, K2 at step 44) that FAILs stops the sequence until the user decides (DESCEND).
5. **Changing this order** needs the user's approval. Then run `uv run python scripts/check_sequence.py` (must print OK)
   and log the change in LOGBOOK.md.
6. **🖥 GPU / 📦 data steps run on the teammate's laptop only** (standing instruction): build and CPU-test everything
   first, write `docs/gpu-runs/T-00NN.md`, push, comment the runbook on the issue, mark WAITING-GPU (or WAITING-DATA), warn
   the user, and continue per rule 2. Downloads are teammate work too. Team manual: `docs/GPU_SETUP.md`.
7. **Build-ahead:** a CODE ticket whose only unfinished dependency is a teammate result (T-0013 preds, T-0065 data) may be
   built and tested on synthetic fixtures. It is then WAITING-DATA, and is closed when the results are pushed and its
   `Done when` is checked on them.

## Teammate sittings (all on the GPU laptop; runbooks in docs/gpu-runs/)
| Sitting | Tickets | Needs | Can start |
|---|---|---|---|
| CPU runs | T-0023, T-0052, T-0037 + T-0038, T-0043 → T-0044 | CPU, Streamlit | now |
| D (data) | T-0065 Part 1 (find, download, licence) | disk, network | now |
| D (data) | T-0065 Part 2 (adapter, crops, audit, window, splits) | the 5 data scripts DONE | after step 34 |
| G2 | T-0012 fold 0 | GPU, crops | after T-0065 + T-0007 freeze |
| G3 | T-0013 full CV + final model | GPU | after G2 is read |
| G4 | T-0036 bench + T-0066 demo (+ T-0067 COULD) | GPU, final.pt | after T-0015 |

## Part A — built before ADR-0009
| Step | Issue / ticket | Title | Owner | Note |
|---|---|---|---|---|
| 1 | [#2](https://github.com/Ayush-3103-AI/SDP/issues/2) T-0002 | Collect the inheritance package from the REU team | HUMAN |  |
| 2 | [#1](https://github.com/Ayush-3103-AI/SDP/issues/1) T-0001 | Scaffold the repo (git, uv project, package, test runner) | CODE |  |
| 3 | [#3](https://github.com/Ayush-3103-AI/SDP/issues/3) T-0003 | Implement the contracts module (dataclasses, constants, JSON round-trip) | CODE |  |
| 4 | [#4](https://github.com/Ayush-3103-AI/SDP/issues/4) T-0004 | Implement the config loader with validation, plus default.yaml and causes.yaml | CODE |  |
| 5 | [#32](https://github.com/Ayush-3103-AI/SDP/issues/32) T-0032 | Implement the SQLite event store | CODE |  |
| 6 | [#21](https://github.com/Ayush-3103-AI/SDP/issues/21) T-0021 | Implement safety gate layers L2 (rate/cooldown) and L1 (physical limits) | CODE |  |
| 7 | [#22](https://github.com/Ayush-3103-AI/SDP/issues/22) T-0022 | Implement gate layer L3 and the event-verdict truth table (with L4) | CODE |  |
| 8 | [#14](https://github.com/Ayush-3103-AI/SDP/issues/14) T-0014 | Implement split-conformal calibration and prediction sets | CODE |  |
| 9 | [#16](https://github.com/Ayush-3103-AI/SDP/issues/16) T-0016 | Implement proposal and counterfactual generation (severity-scaled Δ, G-code, sentence) | CODE |  |
| 10 | [#19](https://github.com/Ayush-3103-AI/SDP/issues/19) T-0019 | Implement the telemetry sensor checks | CODE |  |
| 11 | [#23](https://github.com/Ayush-3103-AI/SDP/issues/23) T-0023 | Write the randomised gate property test and the deck-recipe audit | CODE |  |
| 12 | [#35](https://github.com/Ayush-3103-AI/SDP/issues/35) T-0035 | Implement the outcome verifier | CODE |  |
| 13 | [#26](https://github.com/Ayush-3103-AI/SDP/issues/26) T-0026 | Implement the Printer protocol and the FakePrinter simulator | CODE |  |
| 14 | [#27](https://github.com/Ayush-3103-AI/SDP/issues/27) T-0027 | Implement the OctoPrint REST client | CODE |  |
| 15 | [#29](https://github.com/Ayush-3103-AI/SDP/issues/29) T-0029 | Implement the frame sources (camera and replay folder) | CODE |  |
| 16 | [#30](https://github.com/Ayush-3103-AI/SDP/issues/30) T-0030 | Implement the YOLO11 detector wrapper | CODE |  |
| 17 | [#31](https://github.com/Ayush-3103-AI/SDP/issues/31) T-0031 | Implement the confirmation tracker (with severity) | CODE |  |
| 18 | [#33](https://github.com/Ayush-3103-AI/SDP/issues/33) T-0033 | Implement the orchestrator: baseline mode, critical-first handling, timings, CLI | CODE |  |
| 19 | [#11](https://github.com/Ayush-3103-AI/SDP/issues/11) T-0011 | Implement the cause model (architecture, predict, training step) | CODE |  |
| 20 | [#18](https://github.com/Ayush-3103-AI/SDP/issues/18) T-0018 | Implement EigenCAM attribution on the YOLO11 backbone | CODE |  |
| 21 | [#20](https://github.com/Ayush-3103-AI/SDP/issues/20) T-0020 | Assemble the Explainer (cause model → conformal set → sensor flags → proposals) | CODE |  |
| 22 | [#34](https://github.com/Ayush-3103-AI/SDP/issues/34) T-0034 | Implement the orchestrator's gated-recipe, auto and advisory action paths | CODE |  |
| 23 | [#51](https://github.com/Ayush-3103-AI/SDP/issues/51) T-0051 | Implement operator-decision processing and timeouts in the loop | CODE |  |
| 24 | [#37](https://github.com/Ayush-3103-AI/SDP/issues/37) T-0037 | Build the dashboard live view (read-only) | CODE |  |
| 25 | [#38](https://github.com/Ayush-3103-AI/SDP/issues/38) T-0038 | Build the dashboard proposal cards and operator buttons | CODE |  |
| 26 | [#52](https://github.com/Ayush-3103-AI/SDP/issues/52) T-0052 | Write the 2-hour soak test on replay + FakePrinter | CODE |  |
| 27 | [#43](https://github.com/Ayush-3103-AI/SDP/issues/43) T-0043 | Build the operator-study mode (replay cards with explanation on/off) | CODE |  |
| 28 | [#44](https://github.com/Ayush-3103-AI/SDP/issues/44) T-0044 | Write the operator-study analysis script | CODE |  |

## Part B — software-only plan (ADR-0009)
| Step | Issue / ticket | Title | Owner | Gate / note |
|---|---|---|---|---|
| 29 | [#57](https://github.com/Ayush-3103-AI/SDP/issues/57) T-0057 | Adapt the explain stack to the CAXTON taxonomy (no defect input, manual z-offset causes, SCHEMA_VERSION 2) | CODE | start here |
| 30 | [#5](https://github.com/Ayush-3103-AI/SDP/issues/5) T-0005 | Write the CAXTON adapter (canonical trials.csv / images.csv, label rule, part-stratified subset) | CODE |  |
| 31 | [#9](https://github.com/Ayush-3103-AI/SDP/issues/9) T-0009 | Build the nozzle-ROI crop dataset from images.csv | CODE |  |
| 32 | [#6](https://github.com/Ayush-3103-AI/SDP/issues/6) T-0006 | Write the data audit report (cause coverage per print, single-deviation share, kill check K1′) | CODE | **K1′ kill check** when T-0065 pushes the real audit |
| 33 | [#24](https://github.com/Ayush-3103-AI/SDP/issues/24) T-0024 | Derive the L3 process window from CAXTON's "good" class ranges | CODE |  |
| 34 | [#7](https://github.com/Ayush-3103-AI/SDP/issues/7) T-0007 | Freeze the cause taxonomy and the leave-parts-out splits | PAIR | freeze step after T-0065 |
| 35 | [#65](https://github.com/Ayush-3103-AI/SDP/issues/65) T-0065 | Download CAXTON and run the data sitting on the teammate laptop | HUMAN | 📦 **Teammate data sitting D** (Part 1 can start now: find + download CAXTON, licence) |
| 36 | [#58](https://github.com/Ayush-3103-AI/SDP/issues/58) T-0058 | Wire the Explainer into `xqi run` (with a no-model fallback) and write defects.crop_path | CODE |  |
| 37 | [#59](https://github.com/Ayush-3103-AI/SDP/issues/59) T-0059 | Run EigenCAM on the cause-model backbone | CODE |  |
| 38 | [#60](https://github.com/Ayush-3103-AI/SDP/issues/60) T-0060 | Implement the early-warning module (EWMA + hysteresis) | CODE |  |
| 39 | [#61](https://github.com/Ayush-3103-AI/SDP/issues/61) T-0061 | Add the proactive path to the loop (early-warning events, optional detector) | CODE |  |
| 40 | [#62](https://github.com/Ayush-3103-AI/SDP/issues/62) T-0062 | Add the CAXTON replay source and process-seeded FakePrinter | CODE |  |
| 41 | [#64](https://github.com/Ayush-3103-AI/SDP/issues/64) T-0064 | Write the hand-off package (HANDOFF.md + Printer conformance test) | CODE | **Checkpoint A′:** proactive loop + hand-off run offline on fixtures |
| 42 | [#10](https://github.com/Ayush-3103-AI/SDP/issues/10) T-0010 | Build the cause evaluation harness and the majority floor | CODE |  |
| 43 | [#12](https://github.com/Ayush-3103-AI/SDP/issues/12) T-0012 | Train the cause model on leave-parts-out fold 0 (early read on A3) | PAIR | 🖥 **GPU G2** |
| 44 | [#13](https://github.com/Ayush-3103-AI/SDP/issues/13) T-0013 | Run the full leave-parts-out cross-validation and the K2 kill check | PAIR | 🖥 **GPU G3** · **K2 kill check** |
| 45 | [#15](https://github.com/Ayush-3103-AI/SDP/issues/15) T-0015 | Evaluate conformal coverage on the leave-parts-out folds and save the runtime qhat | CODE | build-ahead (rule 7) |
| 46 | [#17](https://github.com/Ayush-3103-AI/SDP/issues/17) T-0017 | Evaluate counterfactual direction fidelity on confident events | CODE | build-ahead (rule 7) |
| 47 | [#63](https://github.com/Ayush-3103-AI/SDP/issues/63) T-0063 | Evaluate proactive warnings on held-out prints (time-to-warning, recall, false-warning rate) | CODE | build-ahead (rule 7) · **Checkpoint B′:** model + conformal + CF + proactive reports |
| 48 | [#36](https://github.com/Ayush-3103-AI/SDP/issues/36) T-0036 | Write the latency and VRAM report (offline bench) | CODE | 🖥 **GPU G4** (`--bench`) |
| 49 | [#66](https://github.com/Ayush-3103-AI/SDP/issues/66) T-0066 | Run the offline end-to-end HITL demo on held-out CAXTON prints | PAIR | 🖥 **GPU G4** (same sitting) · **Checkpoint C′:** offline HITL demo on real data |
| 50 | [#45](https://github.com/Ayush-3103-AI/SDP/issues/45) T-0045 | Run the operator study sessions | HUMAN | SHOULD |
| 51 | [#46](https://github.com/Ayush-3103-AI/SDP/issues/46) T-0046 | Generate the acceptance report (every FR and NFR → PASS/FAIL with evidence) | CODE |  |
| 52 | [#47](https://github.com/Ayush-3103-AI/SDP/issues/47) T-0047 | Draft the SDP report and paper | PAIR | **Project complete** (MUST/SHOULD) |
| 53 | [#48](https://github.com/Ayush-3103-AI/SDP/issues/48) T-0048 | (COULD) Recalibrate qhat from labelled logged events | CODE | COULD |
| 54 | [#67](https://github.com/Ayush-3103-AI/SDP/issues/67) T-0067 | (COULD) Check domain shift on the inherited camera roll | CODE | COULD · 🖥 teammate laptop |

## Part C — dropped 2026-10-27 (ADR-0009; physical or detector work → integrating team)
| Step | Issue / ticket | Title | Owner | Note |
|---|---|---|---|---|
| 55 | [#8](https://github.com/Ayush-3103-AI/SDP/issues/8) T-0008 | Reproduce the detector baseline on the REU split | CODE | DROPPED |
| 56 | [#25](https://github.com/Ayush-3103-AI/SDP/issues/25) T-0025 | Confirm the envelope numbers and get sign-off | HUMAN | DROPPED |
| 57 | [#28](https://github.com/Ayush-3103-AI/SDP/issues/28) T-0028 | Smoke-test OctoPrint on the real printer and measure dispatch latency | PAIR | DROPPED |
| 58 | [#39](https://github.com/Ayush-3103-AI/SDP/issues/39) T-0039 | Hardware-in-the-loop dry run on the Ender 5 Plus (no induced defects) | PAIR | DROPPED |
| 59 | [#40](https://github.com/Ayush-3103-AI/SDP/issues/40) T-0040 | Write the induced-defect campaign protocol and the randomised run matrix | CODE | DROPPED |
| 60 | [#41](https://github.com/Ayush-3103-AI/SDP/issues/41) T-0041 | Run the induced-defect campaign | HUMAN | DROPPED |
| 61 | [#42](https://github.com/Ayush-3103-AI/SDP/issues/42) T-0042 | Evaluate the rig results (resolution, overshoot, violations, latency by mode) | CODE | DROPPED |
| 62 | [#49](https://github.com/Ayush-3103-AI/SDP/issues/49) T-0049 | (COULD) Test tiled inference for under-extrusion | CODE | DROPPED |
| 63 | [#50](https://github.com/Ayush-3103-AI/SDP/issues/50) T-0050 | (COULD) Evaluate the cause model leave-one-printer-out (Kobra 2 Neo) | PAIR | DROPPED |
