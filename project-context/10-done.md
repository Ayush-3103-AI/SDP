<!-- HEAD
FILE:     10-done.md
PHASE:    3 — DEFINE DONE
UPDATED:  2026-10-03
STATUS:   draft (awaiting gate)
SUMMARY:  A day in the life of an operator in advisory mode; a 5-minute demo for
          Dr. Meti in deck vocabulary; an acceptance matrix mapping all MUST/SHOULD FRs
          and every NFR to a test or report; the verdict statement (matches charter
          S1-S5); the finished artifact tree.
OPEN:     none
-->

# Definition of Done

## Day in the life (advisory mode, Ender 5 Plus, PLA bracket)
1. The operator starts OctoPrint's print, then runs `python -m xqi run --config config/default.yaml --mode advisory` and `python -m xqi ui --run latest`. The dashboard shows the live camera with boxes, nozzle 210/210 °C, bed 60/60 °C, flow 100 %, speed 100 %, mode ADVISORY.
2. At layer ~40, under-extrusion appears. Four frames later a card slides in (< 1 s). It shows:
   - the crop and its heatmap;
   - "**Most likely cause: flow too low (p=0.64)**; also plausible: nozzle too cold (0.22)";
   - "No sensor flags";
   - **Proposal A:** "Flow 100 → 108 % (+8 pp). Gate: L1 ✓ L2 ✓ L3 ✓";
   - **Proposal B:** "Nozzle 210 → 214 °C (+4 °C). Gate: ✓ ✓ ✓".
   The card says why it isn't auto-applied: two causes in the set.
3. The operator suspects the spool and clicks Apply on A. The loop sends `M221 S108`; the dashboard notes "flow cooldown 20 s". 150 s later the event row reads **resolved** (r_before 0.42 → r_after 0.03).
4. Later the operator tries Modify on a nozzle proposal with +15 °C. The loop clips it to +5 °C and the card shows "L2: clipped 15 → 5 °C".
5. Spaghetti appears: M112 is sent immediately, as before. The card arrives afterwards with an explanation.
6. After the print, `python scripts/eval_runs.py runs/<id>` writes resolution rate, reversals, max deviation and latency p95 into `reports/rig_results.md`.

## Five-minute demo for Dr. Meti (deck vocabulary)
1. "Here's the REU loop in `baseline`, unchanged: same recipes, same M112." (30 s)
2. "Recipe audit: the deck's fixed recipes violate the stated envelope in N of M actions, e.g. M104 S190 is a −20 °C step against L2 = 5 °C." (`reports/recipe_audit.md`, 45 s)
3. "Explanation fidelity against induced causes on **unseen geometries**: top-1 X vs floor Y; the conformal set covers Z % at α = 0.1." (`reports/cause_eval.md`, `reports/conformal.md`, 60 s)
4. Live (or recorded) advisory run: an induced flow-low defect gives a card with process-variable reasoning; the operator applies it; resolved. (90 s)
5. "Zero constraint violations across 100 000 randomised cases and every rig run; auto-mode actuation p95 = T s against the 0.21–0.27 s baseline." (45 s)
6. Operator study: accuracy with vs without explanations. (30 s)

## Acceptance matrix
| Req | Verification | Evidence artifact | Ticket |
|---|---|---|---|
| FR-001 | test_modes | pytest log | T-0034 |
| FR-002 | test_camera | pytest | T-0029 |
| FR-003 | test_detect + eval_detector | reports/detector_baseline.md | T-0030, T-0008 |
| FR-004 | test_confirm | pytest | T-0031 |
| FR-005 | test_critical_first | pytest + rig log | T-0033 |
| FR-006 | test_severity | pytest | T-0031 |
| FR-007 | test_cause_model | pytest | T-0011 |
| FR-008 | test_conformal | pytest | T-0014 |
| FR-009 | test_attribution | runs/*/heatmaps | T-0018, T-0034 |
| FR-010 | test_sensors | pytest | T-0019 |
| FR-011 | test_counterfactual | pytest | T-0016 |
| FR-012 | test_gate, test_gate_property | reports/gate_property.md | T-0021, T-0022, T-0023 |
| FR-013 | test_event_verdict_table | pytest | T-0022 |
| FR-014 | test_apply_updates_state | pytest | T-0034 |
| FR-015 | test_ui_data + demo | screenshot in reports/ | T-0037 |
| FR-016 | test_ui_data + demo | screenshot | T-0038 |
| FR-017 | test_modify_regated | pytest | T-0051 |
| FR-018 | test_pause_stop | pytest | T-0051 |
| FR-019 | test_timeout | pytest | T-0051 |
| FR-020 | test_verify | pytest | T-0035 |
| FR-021 | test_store | pytest | T-0032 |
| FR-022 | test_timings_logged | pytest | T-0033 |
| FR-023 | test_baseline_parity | pytest | T-0033 |
| FR-024 | each script | reports/*.md | T-0006…T-0046 |
| FR-025 | test_study + pilot | study.sqlite | T-0043 |
| NFR-001/002/011 | eval_latency | reports/latency.md | T-0036, T-0039, T-0042 |
| NFR-003 | store timestamps | reports/latency.md | T-0039 |
| NFR-004 | gate property + rig logs | reports/gate_property.md, reports/rig_results.md | T-0023, T-0042 |
| NFR-005 | eval_cause | reports/cause_eval.md | T-0013 |
| NFR-006 | eval_conformal | reports/conformal.md | T-0015 |
| NFR-007 | eval_counterfactual | reports/counterfactual.md | T-0017 |
| NFR-008 | soak test (slow) | pytest -m slow log | T-0052 |
| NFR-009 | CI command | pytest timing | every CODE ticket |
| NFR-010 | eval_runs | reports/rig_results.md | T-0042 |

## Verdict statement
**This project is done when:**
- LOGO cause top-1 exceeds the majority-per-class floor by ≥ 10 pp (S1);
- conformal coverage is ≥ 0.85 at α = 0.10 with mean set size ≤ 2.0 (S2);
- post-gate envelope violations are 0 across 100 000 randomised cases and all rig runs (S3);
- auto-mode defect → command latency is p95 ≤ 0.30 s on the Ender 5 Plus with the RTX 3050 (S4);
- the induced-defect campaign shows resolution rate ≥ baseline − 5 pp with fewer setpoint reversals than the deck's fixed recipes (S5).

All of these are recorded in `reports/acceptance.md` and accepted by Dr. Vinod Kumar V Meti.

## Finished artifact tree
See 09-interfaces §Repo layout, plus `reports/`:
```
data_audit.md detector_baseline.md cause_floor.md cause_eval.md conformal.md counterfactual.md
gate_property.md recipe_audit.md l3_window.md octoprint_smoke.md latency.md dry_run.md rig_results.md
operator_study.md acceptance.md
```
