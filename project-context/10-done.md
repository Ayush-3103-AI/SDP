<!-- HEAD
FILE:     10-done.md
PHASE:    3 — DEFINE DONE (delta 2026-10-27, ADR-0009 software-only)
UPDATED:  2026-10-27
STATUS:   accepted delta
SUMMARY:  A day in the life of an operator replaying a held-out CAXTON print in advisory mode; a 5-minute
          demo for Dr. Meti; an acceptance matrix mapping every MUST/SHOULD FR and NFR to a test or report;
          the verdict statement (= ADR-0009 S1–S7); the finished artifact tree; the hand-off package.
          Nothing here needs a printer. The integrating team's rig results are theirs, not ours.
OPEN:     none
-->

# Definition of Done

## Day in the life (advisory mode, offline replay of a held-out CAXTON print)
1. The operator runs `uv run python -m xqi run --config config/caxton_demo.yaml --mode advisory` (camera source
   `caxton:data/crops.csv#p142`, FakePrinter) and `uv run python -m xqi ui --run latest`. The dashboard shows the nozzle
   close-up, nozzle 205/205 °C, flow 100 %, speed 100 %, mode ADVISORY.
2. At image 450 the logged flow drops to 62 %. About 5 s later (EWMA + 3 evaluations) an **early-warning** card
   slides in, before any defect class is confirmed. It shows:
   - the ROI crop and its heatmap (cause-model backbone);
   - "**Early warning: flow too low (p̄=0.71)**; also plausible: speed too high (0.18)";
   - **Proposal A:** "Flow 62 → 72 % (+10 pp). Gate: L1 ✓ L2 ✓ (clipped 14 → 10) L3 ✓ (toward the window)";
   - why it isn't auto-applied: early warnings always need a human (FR-030).
3. The operator clicks Apply. The loop sends `M221 S72` to the FakePrinter; the dashboard notes "flow cooldown 20 s".
4. Later the model warns "nozzle too close to the bed (z_offset_low)". The card shows no setpoint proposal, only the
   advice "raise the Z offset (~0.05 mm)", and the event is ESCALATE (manual cause).
5. The operator tries Modify with +25 pp on a flow proposal. The loop clips it to +10 pp; the card shows
   "L2: clipped 25 → 10 pp".
6. After the replay, the reports show for this print: onsets, time-to-warning per onset, false warnings.

## Five-minute demo for Dr. Meti
1. "The deck's fixed recipes violate the stated envelope in N of M actions, e.g. M104 S190 is a −20 °C step against
   L2 = 5 °C." (`reports/recipe_audit.md`, 45 s)
2. "Cause explanation on **prints the model never saw** (leave-parts-out): top-1 X [CI] vs floor Y; the conformal set
   covers Z % at α = 0.1 with mean size W." (`reports/cause_eval.md`, `reports/conformal.md`, 60 s)
3. "Proactive: median warning T s after a parameter goes wrong, recall R within 30 s, F false warnings per hour."
   (`reports/proactive.md`, 45 s)
4. Recorded advisory replay: early warning → card with heatmap, cause set, gated proposal → operator applies. (90 s)
5. "Zero envelope violations across 100 000 randomised cases and all replay runs; action path p95 = L ms."
   (`reports/gate_property.md`, `reports/latency.md`, 30 s)
6. "Hand-off: the other team implements one `Printer` class and runs our conformance test." (`docs/HANDOFF.md`, 30 s)

## Acceptance matrix
| Req | Verification | Evidence artifact | Ticket |
|---|---|---|---|
| FR-001 | test_modes | pytest log | T-0034 |
| FR-002 | test_camera (replay + caxton source) | pytest | T-0029, T-0062 |
| FR-003 | test_detect (fake model), detector optional in the loop | pytest | T-0030, T-0061 |
| FR-004 | test_confirm | pytest | T-0031 |
| FR-005 | test_critical_first | pytest | T-0033 |
| FR-006 | test_severity | pytest | T-0031 |
| FR-007 | test_cause_model (+ use_defect=false) | pytest | T-0011, T-0057 |
| FR-008 | test_conformal | pytest | T-0014 |
| FR-009 | test_attribution (cause-model backbone) | runs/*/heatmaps | T-0059 |
| FR-010 | test_sensors | pytest | T-0019 |
| FR-011 | test_counterfactual (+ manual causes) | pytest | T-0016, T-0057 |
| FR-012 | test_gate, test_gate_property | reports/gate_property.md | T-0021, T-0022, T-0023 |
| FR-013 | test_event_verdict_table | pytest | T-0022, T-0057 |
| FR-014 | test_apply_updates_state | pytest | T-0034 |
| FR-015 | test_ui_data + demo | reports/img/ui_live.png | T-0037 |
| FR-016 | test_ui_data + demo | reports/img/ui_card.png | T-0038 |
| FR-017 | test_modify_regated | pytest | T-0051 |
| FR-018 | test_pause_stop | pytest | T-0051 |
| FR-019 | test_timeout | pytest | T-0051 |
| FR-020 | test_verify | pytest | T-0035 |
| FR-021 | test_store | pytest | T-0032 |
| FR-022 | test_timings_logged | pytest | T-0033 |
| FR-023 | test_baseline_parity | pytest | T-0033 |
| FR-024 | each script | reports/*.md | T-0006…T-0066 |
| FR-025 | test_study + pilot | study.sqlite | T-0043, T-0045 |
| FR-029 | test_proactive | pytest | T-0060 |
| FR-030 | test_early_warning_never_auto | pytest | T-0061 |
| FR-031 | test_adapt_caxton, test_build_crops | reports/data_audit.md | T-0005, T-0009, T-0006 |
| FR-032 | test_printer_contract | docs/HANDOFF.md | T-0064 |
| NFR-001/011 | eval_latency --bench | reports/latency.md | T-0036 |
| NFR-002/003 | store timings of the replay demo | reports/demo.md | T-0066 |
| NFR-004 | gate property + replay logs | reports/gate_property.md, reports/demo.md | T-0023, T-0066 |
| NFR-005 | eval_cause | reports/cause_eval.md | T-0013 |
| NFR-006 | eval_conformal | reports/conformal.md | T-0015 |
| NFR-007 | eval_counterfactual | reports/counterfactual.md | T-0017 |
| NFR-008 | soak test (slow) | reports/soak_T-0052.txt | T-0052 |
| NFR-009 | CI command | pytest timing | every CODE ticket |
| NFR-012 | eval_proactive | reports/proactive.md | T-0063 |

## Verdict statement
**This project is done when:**
- leave-parts-out cause top-1 exceeds the majority floor by ≥ 10 pp, with a bootstrap 95 % CI over prints (S1);
- conformal coverage is ≥ 0.85 at α = 0.10 with mean set size ≤ 2.0 (S2);
- post-gate envelope violations are 0 across 100 000 randomised cases and all replay runs (S3);
- the action path (cause + conformal + gate) is p95 ≤ 30 ms on the RTX 3050 (S4);
- proactive warnings arrive at a median ≤ 10 s after onset with recall@30 s ≥ 0.70 and ≤ 1 false warning per
  print-hour (S5) [assumed];
- on confident events the top-1 proposal moves the right variable in the right direction ≥ 0.85 of the time (S6);
- the hand-off package exists and FakePrinter passes the Printer conformance test (FR-032);
- (SHOULD) the operator study reports explanation ON vs OFF with CIs (S7).

All of these are recorded in `reports/acceptance.md` and accepted by Dr. Vinod Kumar V Meti. The report states the
domain gap: CAXTON is a nozzle close-up on CR-20 Pro printers in PLA; another camera needs new data (T-0067).

## Finished artifact tree
See 09-interfaces §Repo layout, plus `reports/`:
```
data_audit.md l3_window.md cause_floor.md cause_fold0.md cause_eval.md conformal.md counterfactual.md
proactive.md gate_property.md recipe_audit.md latency.md demo.md soak_T-0052.txt operator_study.md
domain_shift.md (COULD) acceptance.md
```
and `docs/HANDOFF.md`, `docs/data/CAXTON.md`.
