NFR-006: FAIL (coverage 0.909, need ≥ 0.85; mean set size 6.18, need ≤ 2.0; α = 0.1, mean over 5 folds)

# Conformal coverage on the leave-parts-out folds (T-0015)

Predictions: models\cause\recal/preds_fold*.npz. qhat per fold from its calibration prints (training prints); coverage on its held-out test prints; `multi` rows excluded. Leave-parts-out is a shift, so the 1 − α guarantee does not hold: these are empirical values (07 §8).

## Per fold

| fold | α | calib images | qhat | test images | coverage | mean set size |
|---|---|---|---|---|---|---|
| 0 | 0.05 | 5743 | 0.9573 | 8088 | 0.949 | 7.49 |
| 0 | 0.1 | 5743 | 0.9373 | 8088 | 0.884 | 6.31 |
| 0 | 0.2 | 5743 | 0.9161 | 8088 | 0.810 | 5.15 |
| 1 | 0.05 | 6827 | 0.9641 | 8694 | 0.949 | 6.73 |
| 1 | 0.1 | 6827 | 0.9464 | 8694 | 0.900 | 5.63 |
| 1 | 0.2 | 6827 | 0.9213 | 8694 | 0.828 | 4.41 |
| 2 | 0.05 | 7031 | 0.9627 | 7605 | 0.940 | 7.24 |
| 2 | 0.1 | 7031 | 0.9328 | 7605 | 0.896 | 6.02 |
| 2 | 0.2 | 7031 | 0.9109 | 7605 | 0.790 | 4.93 |
| 3 | 0.05 | 7435 | 0.9586 | 7108 | 0.990 | 7.82 |
| 3 | 0.1 | 7435 | 0.9543 | 7108 | 0.969 | 7.07 |
| 3 | 0.2 | 7435 | 0.9322 | 7108 | 0.878 | 5.15 |
| 4 | 0.05 | 5845 | 0.9578 | 7736 | 0.925 | 6.59 |
| 4 | 0.1 | 5845 | 0.9476 | 7736 | 0.894 | 5.88 |
| 4 | 0.2 | 5845 | 0.8911 | 7736 | 0.739 | 4.26 |

## Mean over folds

| α | target 1 − α | coverage | mean set size |
|---|---|---|---|
| 0.05 | 0.95 | 0.951 | 7.17 |
| 0.1 | 0.90 | 0.909 | 6.18 |
| 0.2 | 0.80 | 0.809 | 4.78 |

## Set sizes at α = 0.1 (pooled)

| set size | test images | share |
|---|---|---|
| 1 | 7 | 0.000 |
| 2 | 104 | 0.003 |
| 3 | 370 | 0.009 |
| 4 | 2141 | 0.055 |
| 5 | 6243 | 0.159 |
| 6 | 15802 | 0.403 |
| 7 | 11298 | 0.288 |
| 8 | 2885 | 0.074 |
| 9 | 381 | 0.010 |

## Coverage per cause at α = 0.1 (pooled)

| cause | test images | coverage |
|---|---|---|
| none | 6968 | 0.996 |
| flow_low | 3168 | 0.939 |
| flow_high | 6574 | 0.990 |
| speed_low | 4761 | 0.928 |
| speed_high | 4128 | 0.934 |
| nozzle_temp_low | 1358 | 0.286 |
| nozzle_temp_high | 830 | 0.106 |
| z_offset_low | 1522 | 0.334 |
| z_offset_high | 9922 | 0.999 |

## Runtime qhat

models\cause\recal\qhat.json: qhat = 0.9386 at α = 0.1 from 5657 calibration images of models\cause\recal\preds_final.npz.
