K2: FAIL (top-1 = floor + -4.5 pp ≤ 5 pp)
NFR-005: FAIL (top-1 = floor + -4.5 pp, need ≥ 10; 95 % CI [0.179, 0.244]; top-3 = 0.501, need ≥ 0.9)

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

Predictions: models/cause/finetune_full/preds_fold*.npz (5 folds; `multi` rows excluded). CIs: bootstrap over test prints (B = 1000), stratified by fold.
- fold 0: 4 epochs, batch 32, best calib loss 2.3702
- fold 1: 6 epochs, batch 32, best calib loss 2.1760
- fold 2: 5 epochs, batch 32, best calib loss 2.3653
- fold 3: 4 epochs, batch 32, best calib loss 2.5704
- fold 4: 5 epochs, batch 32, best calib loss 2.6715

## Result

### Per fold

| fold | test prints | test images | top-1 | 95 % CI | top-3 | floor top-1 | floor top-3 | gap to floor (pp) | gap to oracle | ECE |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 28 | 8088 | 0.211 | [0.141, 0.302] | 0.506 | 0.195 | 0.558 | +1.7 | 0.789 | 0.293 |
| 1 | 49 | 8694 | 0.208 | [0.153, 0.284] | 0.506 | 0.271 | 0.678 | -6.3 | 0.792 | 0.307 |
| 2 | 28 | 7605 | 0.206 | [0.143, 0.281] | 0.502 | 0.228 | 0.602 | -2.2 | 0.794 | 0.267 |
| 3 | 29 | 7108 | 0.212 | [0.158, 0.291] | 0.500 | 0.306 | 0.590 | -9.4 | 0.788 | 0.167 |
| 4 | 29 | 7736 | 0.209 | [0.137, 0.310] | 0.491 | 0.269 | 0.554 | -6.0 | 0.791 | 0.266 |
| mean ± std | 163 | 39231 | 0.209 ± 0.002 | [0.179, 0.244] | 0.501 ± 0.006 | 0.254 ± 0.038 | 0.596 ± 0.045 | -4.5 | 0.791 | 0.260 ± 0.049 |

### Per-class recall (pooled over folds)

| cause | test images | recall |
|---|---|---|
| none | 6968 | 0.421 |
| flow_low | 3168 | 0.192 |
| flow_high | 6574 | 0.154 |
| speed_low | 4761 | 0.145 |
| speed_high | 4128 | 0.156 |
| nozzle_temp_low | 1358 | 0.113 |
| nozzle_temp_high | 830 | 0.052 |
| z_offset_low | 1522 | 0.175 |
| z_offset_high | 9922 | 0.188 |

Balanced accuracy (mean recall over the 9 causes present; report only, not K2): 0.177 (always-majority = 1/9 = 0.111).

### Confusion matrix (pooled; rows = true, columns = predicted)

| true \ pred | none | flow_low | flow_high | speed_low | speed_high | nozzle_temp_low | nozzle_temp_high | z_offset_low | z_offset_high |
|---|---|---|---|---|---|---|---|---|---|
| none | 2932 | 442 | 524 | 493 | 478 | 218 | 638 | 61 | 1182 |
| flow_low | 156 | 607 | 101 | 207 | 594 | 177 | 147 | 413 | 766 |
| flow_high | 672 | 676 | 1011 | 630 | 741 | 324 | 680 | 475 | 1365 |
| speed_low | 599 | 735 | 400 | 689 | 561 | 187 | 522 | 367 | 701 |
| speed_high | 249 | 475 | 373 | 287 | 645 | 188 | 352 | 469 | 1090 |
| nozzle_temp_low | 99 | 168 | 31 | 56 | 297 | 154 | 235 | 64 | 254 |
| nozzle_temp_high | 123 | 35 | 13 | 105 | 135 | 84 | 43 | 29 | 263 |
| z_offset_low | 52 | 158 | 103 | 115 | 355 | 122 | 122 | 266 | 229 |
| z_offset_high | 918 | 1597 | 864 | 815 | 1458 | 529 | 975 | 905 | 1861 |

## Risks

- Most confident wrong test crops (automated visual review of reports/cause_errors_full.png): repeated flow_high predictions at p=1.00 on true z_offset_high and none crops; the tightly framed, visually similar nozzle/filament ROIs may omit print-bed context that could distinguish offset errors from flow errors.
- Staleness: trained on CAXTON's nozzle close-up camera, its printer and PLA. A new printer, camera pose or zoom, or material is a new distribution: re-run T-0013 on its data before trusting top-1 (NFR-005) or the conformal coverage (T-0015).
- Within-print leakage reference (random-by-image split on fold 0, SHOULD): not run.

