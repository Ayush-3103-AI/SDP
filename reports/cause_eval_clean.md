K2: FAIL (top-1 = floor + -7.0 pp ≤ 5 pp)
NFR-005: FAIL (top-1 = floor + -7.0 pp, need ≥ 10; 95 % CI [0.167, 0.234]; top-3 = 0.492, need ≥ 0.9)

# Cause model evaluation (T-0010, T-0013)

## Frame

- Decision: which setpoint proposal(s) the operator sees for a confirmed defect.
- Unit: one 224 px crop (nozzle ROI, or a confirmed defect box) at decision time.
- Target: the image's process deviation (07 §15 label rule).
- Metric: LOGO mean top-1 (NFR-005). Error cost: a wrong actionable cause proposes a
  wrong-direction change (bounded by the gate), so per-class recall on actionable causes
  is the main diagnostic.
- Baseline: the floor, i.e. the training prints' majority cause (T-0010; CAXTON has no defect class).

## Baseline

Floor = the fold's training-print majority cause, predicted for every test image (07 §9; reports/cause_floor.md). Oracle = the CAXTON parameter class (top-1 = 1.0), so gap to oracle = 1 − top-1. K2 fires at ≤ floor + 5 pp (charter); NFR-005 needs ≥ floor + 10 pp and top-3 ≥ 0.90.

## Model

Predictions: models/cause/raw_clean/preds_fold*.npz (5 folds; `multi` rows excluded). CIs: bootstrap over test prints (B = 1000), stratified by fold.

## Result

### Per fold

| fold | test prints | test images | top-1 | 95 % CI | top-3 | floor top-1 | floor top-3 | gap to floor (pp) | gap to oracle | ECE |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 27 | 6663 | 0.204 | [0.136, 0.294] | 0.506 | 0.198 | 0.573 | +0.6 | 0.796 | 0.304 |
| 1 | 46 | 7125 | 0.205 | [0.145, 0.279] | 0.506 | 0.287 | 0.691 | -8.2 | 0.795 | 0.305 |
| 2 | 27 | 6178 | 0.170 | [0.110, 0.238] | 0.476 | 0.247 | 0.625 | -7.8 | 0.830 | 0.299 |
| 3 | 29 | 5944 | 0.203 | [0.150, 0.283] | 0.494 | 0.315 | 0.601 | -11.2 | 0.797 | 0.168 |
| 4 | 27 | 6273 | 0.211 | [0.136, 0.310] | 0.478 | 0.295 | 0.592 | -8.4 | 0.789 | 0.262 |
| mean ± std | 156 | 32183 | 0.199 ± 0.015 | [0.167, 0.234] | 0.492 ± 0.013 | 0.269 ± 0.042 | 0.617 ± 0.041 | -7.0 | 0.801 | 0.268 ± 0.052 |

### Per-class recall (pooled over folds)

| cause | test images | recall |
|---|---|---|
| none | 5594 | 0.378 |
| flow_low | 2725 | 0.204 |
| flow_high | 5683 | 0.150 |
| speed_low | 4121 | 0.141 |
| speed_high | 3503 | 0.159 |
| nozzle_temp_low | 1209 | 0.112 |
| nozzle_temp_high | 721 | 0.050 |
| z_offset_low | 7 | 0.000 |
| z_offset_high | 8620 | 0.183 |

Balanced accuracy (mean recall over the 9 causes present; report only, not K2): 0.153 (always-majority = 1/9 = 0.111).

### Confusion matrix (pooled; rows = true, columns = predicted)

| true \ pred | none | flow_low | flow_high | speed_low | speed_high | nozzle_temp_low | nozzle_temp_high | z_offset_low | z_offset_high |
|---|---|---|---|---|---|---|---|---|---|
| none | 2115 | 392 | 437 | 446 | 362 | 182 | 546 | 54 | 1060 |
| flow_low | 117 | 555 | 98 | 182 | 506 | 161 | 125 | 353 | 628 |
| flow_high | 554 | 585 | 852 | 551 | 645 | 284 | 597 | 414 | 1201 |
| speed_low | 504 | 653 | 357 | 580 | 490 | 134 | 467 | 328 | 608 |
| speed_high | 154 | 400 | 306 | 239 | 557 | 181 | 306 | 407 | 953 |
| nozzle_temp_low | 81 | 152 | 28 | 47 | 273 | 135 | 218 | 59 | 216 |
| nozzle_temp_high | 112 | 25 | 9 | 94 | 121 | 79 | 36 | 26 | 219 |
| z_offset_low | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 4 |
| z_offset_high | 754 | 1420 | 756 | 726 | 1278 | 461 | 846 | 803 | 1576 |

## Risks

- Most confident wrong test crops: reports/cause_errors.png. What the reviewer saw: <fill in after looking: e.g. mislabelled transition frames, nozzle out of the crop, blur>
- Staleness: trained on CAXTON's nozzle close-up camera, its printer and PLA. A new printer, camera pose or zoom, or material is a new distribution: re-run T-0013 on its data before trusting top-1 (NFR-005) or the conformal coverage (T-0015).
- Within-print leakage reference (random-by-image split on fold 0, SHOULD): not run.
