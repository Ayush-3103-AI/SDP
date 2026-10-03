<!-- HEAD
FILE:     11-tickets/SEQUENCE.md
PHASE:    5 — EXECUTE
UPDATED:  2026-10-03
STATUS:   active — THE canonical implementation order
SUMMARY:  52 tickets in one strict order (dependency-checked: no ticket precedes its dependencies).
          Steps 1–26 need no REU data; 27–37 need the T-0002 hand-over; 38–42 need the printer;
          43–49 are the campaign, study and report; 50–52 are stretch. The next ticket is always the
          first step not marked DONE in BOARD.md, unless it's blocked (see the rules below).
OPEN:     none
-->

# Implementation sequence

## Rules
1. **The next ticket is the lowest-numbered step that isn't DONE.** Don't reorder, and don't do two at once (one ticket per session).
2. **Blocked on a human** (HUMAN/PAIR owner, or a dependency waiting on T-0002, T-0025 or T-0041): skip to the next
   step whose dependencies are all DONE, then come back to the skipped step as soon as it unblocks. Note every skip in LOGBOOK.md.
3. **HUMAN steps** are never executed by Claude Code. It tells the user what's needed and moves on per rule 2.
4. **A kill check** (steps 28, 35, 42) that FAILs stops the sequence until the user decides (DESCEND).
5. **Changing this order** needs the user's approval. Then run `python scripts/check_sequence.py` (it must print OK)
   and log the change in LOGBOOK.md.

## Order
| Step | Issue / ticket | Title | Owner | Phase | Gate / note |
|---|---|---|---|---|---|
| 1 | [#2](https://github.com/Ayush-3103-AI/SDP/issues/2) T-0002 | Collect the inheritance package from the REU team | HUMAN | P1 | Start on Day 1 and keep going in the background; steps 27+ need it |
| 2 | [#1](https://github.com/Ayush-3103-AI/SDP/issues/1) T-0001 | Scaffold the repo (git, uv project, package, test runner) | CODE | P1 |  |
| 3 | [#3](https://github.com/Ayush-3103-AI/SDP/issues/3) T-0003 | Implement the contracts module (dataclasses, constants, JSON round-trip) | CODE | P1 |  |
| 4 | [#4](https://github.com/Ayush-3103-AI/SDP/issues/4) T-0004 | Implement the config loader with validation, plus default.yaml and causes.yaml | CODE | P1 |  |
| 5 | [#32](https://github.com/Ayush-3103-AI/SDP/issues/32) T-0032 | Implement the SQLite event store | CODE | P1 |  |
| 6 | [#21](https://github.com/Ayush-3103-AI/SDP/issues/21) T-0021 | Implement safety gate layers L2 (rate/cooldown) and L1 (physical limits) | CODE | P2 |  |
| 7 | [#22](https://github.com/Ayush-3103-AI/SDP/issues/22) T-0022 | Implement gate layer L3 and the event-verdict truth table (with L4) | CODE | P2 |  |
| 8 | [#14](https://github.com/Ayush-3103-AI/SDP/issues/14) T-0014 | Implement split-conformal calibration and prediction sets | CODE | P2 |  |
| 9 | [#16](https://github.com/Ayush-3103-AI/SDP/issues/16) T-0016 | Implement proposal and counterfactual generation (severity-scaled Δ, G-code, sentence) | CODE | P2 |  |
| 10 | [#19](https://github.com/Ayush-3103-AI/SDP/issues/19) T-0019 | Implement the telemetry sensor checks | CODE | P2 |  |
| 11 | [#23](https://github.com/Ayush-3103-AI/SDP/issues/23) T-0023 | Write the randomised gate property test and the deck-recipe audit | CODE | P2 |  |
| 12 | [#35](https://github.com/Ayush-3103-AI/SDP/issues/35) T-0035 | Implement the outcome verifier | CODE | P2 |  |
| 13 | [#26](https://github.com/Ayush-3103-AI/SDP/issues/26) T-0026 | Implement the Printer protocol and the FakePrinter simulator | CODE | P3 |  |
| 14 | [#27](https://github.com/Ayush-3103-AI/SDP/issues/27) T-0027 | Implement the OctoPrint REST client | CODE | P3 |  |
| 15 | [#29](https://github.com/Ayush-3103-AI/SDP/issues/29) T-0029 | Implement the frame sources (camera and replay folder) | CODE | P3 |  |
| 16 | [#30](https://github.com/Ayush-3103-AI/SDP/issues/30) T-0030 | Implement the YOLO11 detector wrapper | CODE | P3 |  |
| 17 | [#31](https://github.com/Ayush-3103-AI/SDP/issues/31) T-0031 | Implement the confirmation tracker (with severity) | CODE | P3 |  |
| 18 | [#33](https://github.com/Ayush-3103-AI/SDP/issues/33) T-0033 | Implement the orchestrator: baseline mode, critical-first handling, timings, CLI | CODE | P3 |  |
| 19 | [#11](https://github.com/Ayush-3103-AI/SDP/issues/11) T-0011 | Implement the cause model (architecture, predict, training step) | CODE | P4 |  |
| 20 | [#18](https://github.com/Ayush-3103-AI/SDP/issues/18) T-0018 | Implement EigenCAM attribution on the YOLO11 backbone | CODE | P4 |  |
| 21 | [#20](https://github.com/Ayush-3103-AI/SDP/issues/20) T-0020 | Assemble the Explainer (cause model → conformal set → sensor flags → proposals) | CODE | P4 |  |
| 22 | [#34](https://github.com/Ayush-3103-AI/SDP/issues/34) T-0034 | Implement the orchestrator's gated-recipe, auto and advisory action paths | CODE | P5 |  |
| 23 | [#51](https://github.com/Ayush-3103-AI/SDP/issues/51) T-0051 | Implement operator-decision processing and timeouts in the loop | CODE | P5 |  |
| 24 | [#37](https://github.com/Ayush-3103-AI/SDP/issues/37) T-0037 | Build the dashboard live view (read-only) | CODE | P5 |  |
| 25 | [#38](https://github.com/Ayush-3103-AI/SDP/issues/38) T-0038 | Build the dashboard proposal cards and operator buttons | CODE | P5 |  |
| 26 | [#52](https://github.com/Ayush-3103-AI/SDP/issues/52) T-0052 | Write the 2-hour soak test on replay + FakePrinter | CODE | P5 | **Checkpoint A:** the full loop runs offline (replay + FakePrinter, stub model) |
| 27 | [#5](https://github.com/Ayush-3103-AI/SDP/issues/5) T-0005 | Write the induction-log adapter to the canonical trials.csv and images.csv | CODE | P6 |  |
| 28 | [#6](https://github.com/Ayush-3103-AI/SDP/issues/6) T-0006 | Write the data audit report (join rate, cause coverage, kill check K1) | CODE | P6 | **K1 kill check**: on FAIL, stop and propose a DESCEND |
| 29 | [#7](https://github.com/Ayush-3103-AI/SDP/issues/7) T-0007 | Freeze the cause taxonomy and the LOGO splits | PAIR | P6 |  |
| 30 | [#8](https://github.com/Ayush-3103-AI/SDP/issues/8) T-0008 | Reproduce the detector baseline on the REU split | CODE | P6 |  |
| 31 | [#24](https://github.com/Ayush-3103-AI/SDP/issues/24) T-0024 | Derive the L3 process window from the trial log | CODE | P6 |  |
| 32 | [#9](https://github.com/Ayush-3103-AI/SDP/issues/9) T-0009 | Build the crop dataset from labelled boxes | CODE | P6 |  |
| 33 | [#10](https://github.com/Ayush-3103-AI/SDP/issues/10) T-0010 | Build the cause evaluation harness and the floor baseline | CODE | P6 |  |
| 34 | [#12](https://github.com/Ayush-3103-AI/SDP/issues/12) T-0012 | Train the cause model on one LOGO fold (early spike for A3) | PAIR | P6 |  |
| 35 | [#13](https://github.com/Ayush-3103-AI/SDP/issues/13) T-0013 | Run the full LOGO cross-validation and the K2 kill check | PAIR | P6 | **K2 kill check**: on FAIL, stop and propose a DESCEND |
| 36 | [#15](https://github.com/Ayush-3103-AI/SDP/issues/15) T-0015 | Evaluate conformal coverage on the LOGO folds and save the runtime qhat | CODE | P6 |  |
| 37 | [#17](https://github.com/Ayush-3103-AI/SDP/issues/17) T-0017 | Evaluate counterfactual direction fidelity and steps-to-undo | CODE | P6 | **Checkpoint B:** real model + qhat + eval reports done |
| 38 | [#25](https://github.com/Ayush-3103-AI/SDP/issues/25) T-0025 | Confirm the envelope numbers and get sign-off | HUMAN | P7 |  |
| 39 | [#28](https://github.com/Ayush-3103-AI/SDP/issues/28) T-0028 | Smoke-test OctoPrint on the real printer and measure dispatch latency | PAIR | P7 |  |
| 40 | [#36](https://github.com/Ayush-3103-AI/SDP/issues/36) T-0036 | Write the latency and VRAM report | CODE | P7 |  |
| 41 | [#40](https://github.com/Ayush-3103-AI/SDP/issues/40) T-0040 | Write the induced-defect campaign protocol and the randomised run matrix | CODE | P7 |  |
| 42 | [#39](https://github.com/Ayush-3103-AI/SDP/issues/39) T-0039 | Hardware-in-the-loop dry run on the Ender 5 Plus (no induced defects) | PAIR | P7 | **K3 check** + **Checkpoint C:** the real printer works (end of the 4-week plan) |
| 43 | [#43](https://github.com/Ayush-3103-AI/SDP/issues/43) T-0043 | Build the operator-study mode (replay cards with explanation on/off) | CODE | Post |  |
| 44 | [#44](https://github.com/Ayush-3103-AI/SDP/issues/44) T-0044 | Write the operator-study analysis script | CODE | Post |  |
| 45 | [#41](https://github.com/Ayush-3103-AI/SDP/issues/41) T-0041 | Run the induced-defect campaign | HUMAN | Post |  |
| 46 | [#42](https://github.com/Ayush-3103-AI/SDP/issues/42) T-0042 | Evaluate the rig results (resolution, overshoot, violations, latency by mode) | CODE | Post |  |
| 47 | [#45](https://github.com/Ayush-3103-AI/SDP/issues/45) T-0045 | Run the operator study sessions | HUMAN | Post |  |
| 48 | [#46](https://github.com/Ayush-3103-AI/SDP/issues/46) T-0046 | Generate the acceptance report (every FR and NFR → PASS/FAIL with evidence) | CODE | Post |  |
| 49 | [#47](https://github.com/Ayush-3103-AI/SDP/issues/47) T-0047 | Draft the SDP report and paper | PAIR | Post | **Project complete** (MUST/SHOULD) |
| 50 | [#48](https://github.com/Ayush-3103-AI/SDP/issues/48) T-0048 | (COULD) Recalibrate qhat from labelled logged events | CODE | Stretch |  |
| 51 | [#49](https://github.com/Ayush-3103-AI/SDP/issues/49) T-0049 | (COULD) Test tiled inference for under-extrusion | CODE | Stretch |  |
| 52 | [#50](https://github.com/Ayush-3103-AI/SDP/issues/50) T-0050 | (COULD) Evaluate the cause model leave-one-printer-out (Kobra 2 Neo) | PAIR | Stretch |  |
