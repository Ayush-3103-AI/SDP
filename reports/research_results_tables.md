# Research-ready results tables (GPU sitting 2026-11-16)

Prepared 2026-11-20 from the run outputs listed under each table. Values below are reported results, not re-estimated statistics. The operator study and T-0066 advisory demo remain incomplete; their partial data are not presented as final participant or human-in-the-loop evidence.

## Table 1. Dataset and evaluation cohort

| Measure | Result | Source / definition |
|---|---:|---|
| Kept CAXTON images | 79,515 | `reports/data_audit.md`; frozen image manifest hash matched the runbook |
| Prints | 181 | CAXTON `trials.csv`, as reported in `reports/data_audit.md` |
| Crops without source images | 0 / 79,515 | Complete-data audit (`reports/data_audit.md`) |
| Evaluation design | 5 leave-one-group-out folds | `data/splits/logo.json`; `multi` rows excluded in the model reports |
| Held-out test images | 39,231 | Sum across five folds (`reports/cause_eval_full.md`) |
| Held-out test prints | 163 (fold total) | Fold counts in `reports/cause_eval_full.md`; do not interpret as unique pooled subjects without the split definition |

### Single-cause data availability

| Cause | Images | Prints |
|---|---:|---:|
| flow_low | 3,168 | 45 |
| flow_high | 6,574 | 64 |
| speed_low | 4,761 | 59 |
| speed_high | 4,128 | 55 |
| nozzle_temp_low | 1,358 | 22 |
| nozzle_temp_high | 830 | 18 |
| z_offset_low | 1,522 | 84 |
| z_offset_high | 9,922 | 102 |

Source: `reports/data_audit.md`. Multi-cause rows are not included in this table.

## Table 2. Cause classifier performance by held-out fold

| Fold | Test prints | Test images | Top-1 | 95% CI | Top-3 | Floor top-1 | Gap to floor (pp) | ECE |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 28 | 8,088 | 0.211 | [0.141, 0.302] | 0.506 | 0.195 | +1.7 | 0.293 |
| 1 | 49 | 8,694 | 0.208 | [0.153, 0.284] | 0.506 | 0.271 | −6.3 | 0.307 |
| 2 | 28 | 7,605 | 0.206 | [0.143, 0.281] | 0.502 | 0.228 | −2.2 | 0.267 |
| 3 | 29 | 7,108 | 0.212 | [0.158, 0.291] | 0.500 | 0.306 | −9.4 | 0.167 |
| 4 | 29 | 7,736 | 0.209 | [0.137, 0.310] | 0.491 | 0.269 | −6.0 | 0.266 |
| Mean ± SD | 163 fold-print counts | 39,231 | 0.209 ± 0.002 | [0.179, 0.244] | 0.501 ± 0.006 | 0.254 ± 0.038 | −4.5 | 0.260 ± 0.049 |

| Aggregate diagnostic | Result |
|---|---:|
| Balanced accuracy | 0.177 |
| Always-majority balanced accuracy reference | 0.111 (1/9) |
| K2 kill criterion | FAIL: top-1 is floor − 4.5 percentage points (threshold: floor + 5 pp) |
| NFR-005 | FAIL: top-1 floor gap −4.5 pp (target ≥ +10 pp); top-3 0.501 (target ≥ 0.90) |

Source: `reports/cause_eval_full.md`. Confidence intervals are bootstrapped over test prints (B=1,000), stratified by fold. Fold-mean intervals/uncertainty should be described according to that procedure, not as an image-level IID interval.

## Table 3. Pooled per-cause recall

| Cause | Test images | Recall |
|---|---:|---:|
| none | 6,968 | 0.421 |
| flow_low | 3,168 | 0.192 |
| flow_high | 6,574 | 0.154 |
| speed_low | 4,761 | 0.145 |
| speed_high | 4,128 | 0.156 |
| nozzle_temp_low | 1,358 | 0.113 |
| nozzle_temp_high | 830 | 0.052 |
| z_offset_low | 1,522 | 0.175 |
| z_offset_high | 9,922 | 0.188 |

Source: `reports/cause_eval_full.md`; pooled across folds.

## Table 4. Conformal prediction on held-out prints

| α | Nominal coverage (1−α) | Empirical coverage | Mean prediction-set size | NFR-006 outcome |
|---:|---:|---:|---:|---|
| 0.05 | 0.95 | 0.951 | 7.78 | Not the selected operating point |
| 0.10 | 0.90 | 0.914 | 7.10 | FAIL: target set size ≤2.0 not met |
| 0.20 | 0.80 | 0.815 | 5.80 | Not the selected operating point |

At α=0.10, the pooled set-size distribution was: size 1, 824 (2.1%); size 2, 1,089 (2.8%); size 3, 1,661 (4.2%); size 4, 2,014 (5.1%); size 5, 2,790 (7.1%); size 6, 4,365 (11.1%); size 7, 5,247 (13.4%); size 8, 6,607 (16.8%); size 9, 14,634 (37.3%).

Source: `reports/conformal.md`. These are empirical leave-prints-out values under distribution shift; the report explicitly notes that the exchangeability coverage guarantee does not apply to this split.

## Table 5. Counterfactual direction fidelity on confident actionable predictions

| Evaluation | Actionable images/events | Confident | Confident fraction | Direction fidelity | Target | Outcome |
|---|---:|---:|---:|---:|---:|---|
| Pooled, 5 folds | 20,819 images | 137 events | 0.7% | 0.723 | ≥0.85 | NFR-007 FAIL |

| Cause | Actionable images | Confident | Confident fraction | Fidelity |
|---|---:|---:|---:|---:|
| flow_low | 3,168 | 1 | 0.0% | 0.000 |
| flow_high | 6,574 | 111 | 1.7% | 0.838 |
| speed_low | 4,761 | 1 | 0.0% | 1.000 |
| speed_high | 4,128 | 14 | 0.3% | 0.000 |
| nozzle_temp_low | 1,358 | 10 | 0.7% | 0.500 |
| nozzle_temp_high | 830 | 0 | 0.0% | Not estimable |

Source: `reports/counterfactual.md`. Confidence requires a singleton non-`none` set and top probability ≥0.6. The report uses median absolute logged deviation as a proxy for steps-to-undo because deviation magnitudes vary within a cause.

## Table 6. Proactive warning performance

| Method / held-out result | Median time-to-warning | Recall within 30 s | False warnings per hour | Target | Outcome |
|---|---:|---:|---:|---|---|
| EWMA early-warning system, pooled 5 folds | 7.4 s | 0.01 | 0.85 | ≤10 s; ≥0.70 recall; ≤1 false/h | NFR-012 FAIL: recall target missed |
| Floor baseline (β=0) | 6.5 s | 0.01 | 1.07 | Same targets | Below false-warning target |

Source: `reports/proactive.md`. Thresholds were selected on calibration prints per fold; onset and warning definitions follow that report.

## Table 7. Runtime and GPU latency

| Measurement | Result | Acceptance / interpretation |
|---|---:|---|
| GPU | NVIDIA GeForce RTX 4050 Laptop GPU | Local GPU bench |
| Cause action path p50 / p95 / p99 / max | 3.9 / 4.4 / 4.9 / 5.7 ms | NFR-001 PASS (p95 ≤30 ms) |
| EigenCAM p50 / p95 / p99 | 6.9 / 7.5 / 9.0 ms | Measured after dispatch; excluded from NFR-001 |
| Peak allocated VRAM | 0.11 GB | NFR-011 PASS (≤3.5 GB) |
| Detector | Not configured | Limitation of this bench |

Source: `reports/latency.md`; 500 distinct CAXTON crops. The separate run-store evaluation for T-0066 auto mode reported 3 event-to-cause samples (p50 0.0, p95 14.4, max 16.0 ms); it had zero auto-dispatch latency samples because warning events are not auto-applied. Source: `reports/latency_runs.md`.

## Table 8. T-0066 offline auto-mode demo on held-out prints

| Print | Fold | Logged onsets | Events | Verdicts | Operator decisions | Commands sent | Gate violations |
|---|---:|---:|---:|---|---:|---:|---:|
| p102 | 2 | 7 | 2 | ESCALATE 2 | 2 | 0 | 0 |
| p103 | 3 | 56 | 1 | ESCALATE 1 | 1 | 0 | 0 |
| p107 | 4 | 54 | 0 | — | 0 | 0 | 0 |

| Demo requirement | Result |
|---|---|
| NFR-002 frame-to-verdict | PASS: p95 47 ms, n=3 (limit 300 ms) |
| NFR-003 event-to-card display | FAIL: p95 35,440 ms across 4 shown cards (target ≤1,000 ms) |
| NFR-004 dispatched setpoint safety | PASS: 0 violations in 0 dispatched commands |

Source: `reports/demo.md`. Run plan was fixed before execution (seed 0; one print per three test folds). Advisory outcomes are summarized separately below; their incomplete, partly timed-out trials are not operator-performance evidence.

## Table 9. Operator-study status (not a publishable outcome)

| Data check | Current local pilot database | Protocol expectation | Status |
|---|---:|---:|---|
| Block 1 OFF choices | 24 | 12 | Incomplete/over-counted; do not analyze as a completed single participant |
| Block 2 ON choices | 17 | 12 | Incomplete/over-counted; do not analyze as a completed single participant |
| OFF surveys | 2 | 1 | Extra/inconsistent |
| ON surveys | 1 | 1 | Count alone does not establish completeness |

Source: a read-only count of `reports/study/pilot.sqlite` on 2026-11-20. The T-0043 protocol requires exactly 12 decisions per block and one survey per block for participant 1. Reconcile/restart only under the protocol with the facilitator; no study rows were changed here. Do not use this table as participant-effect evidence.

## Interpretation limits

The complete-data cause model did not outperform the fold-specific majority floor, conformal sets were too large for the specified utility target, and confident counterfactual coverage was sparse. These results do not support presenting cause recommendations as reliable operator guidance. The GPU timing result is favorable for the measured cause-model path, but excludes a configured detector and does not establish full camera-to-action latency. T-0066 auto safety checks passed for the observed runs, but the advisory phase was incomplete (blocked proposals and timeouts) and the operator-study pilot is not valid for analysis.

## Table 10. T-0066 advisory-mode outcomes

| Print attempt | Events | Recorded decision rows | Result |
|---|---:|---:|---|
| p102 | 2 | 2 Modify | Both blocked by the L1 flow envelope; no command dispatched |
| p103 | 1 | 1 timeout | No operator decision before timeout |
| p103 retry | 1 | 1 timeout | No operator decision before timeout |
| p107 | 0 | 0 | No cards presented |

Across auto and advisory runs, NFR-002 was PASS (p95 47 ms, n=7), NFR-003 was FAIL (p95 35,440 ms, n=4, target ≤1 s), and NFR-004 was PASS with 0 violations in 0 dispatched commands. The NFR-004 result is a zero-command check and does not demonstrate an applied setpoint. Source: `reports/demo.md`.

## Table 11. Automated checks

| Check | Result | Limitation |
|---|---|---|
| Main-branch full suite (step 0) | 343 passed, 1 skipped, 6 deselected | Python-module pytest workaround; direct launcher was blocked by Windows Application Control |
| T-0038 UI-data tests | 14 passed | Workspace `ui_card.png` is an old synthetic-frame capture, not evidence for the new CAXTON-backed run |
| T-0043 study/UI tests | 20 passed | Software tests only; current pilot DB has duplicate/incomplete study rows |
| T-0044 analyzer tests | 3 passed | Unsandboxed retry required for SQLite temporary-file access |
| T-0044 analyzer selftest | Passed | Synthetic benchmark: +9.2 pp accuracy, 95% CI [+3.1, +15.4] |
| T-0066 demo/store tests | 18 passed, 1 failed | `run_demo.selftest` discovery error: `ValueError: not enough values to unpack`; no code fix applied |
| T-0066 report selftest | Failed | Same run-discovery error; traceback posted on #66 |

Automated checks are software evidence. They do not replace the T-0043 human participant study or a valid full-window T-0038 proposal-card screenshot.

