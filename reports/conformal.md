NFR-006: FAIL (coverage 0.914, need ≥ 0.85; mean set size 7.10, need ≤ 2.0; α = 0.1, mean over 5 folds)

# Conformal coverage on the leave-parts-out folds (T-0015)

Predictions: models\cause/preds_fold*.npz. qhat per fold from its calibration prints (training prints); coverage on its held-out test prints; `multi` rows excluded. Leave-parts-out is a shift, so the 1 − α guarantee does not hold: these are empirical values (07 §8).

## Per fold

| fold | α | calib images | qhat | test images | coverage | mean set size |
|---|---|---|---|---|---|---|
| 0 | 0.05 | 5743 | 0.9918 | 8088 | 0.921 | 7.25 |
| 0 | 0.1 | 5743 | 0.9866 | 8088 | 0.879 | 6.62 |
| 0 | 0.2 | 5743 | 0.9725 | 8088 | 0.781 | 5.41 |
| 1 | 0.05 | 6827 | 0.9946 | 8694 | 0.934 | 7.27 |
| 1 | 0.1 | 6827 | 0.9881 | 8694 | 0.885 | 6.52 |
| 1 | 0.2 | 6827 | 0.9687 | 8694 | 0.771 | 5.16 |
| 2 | 0.05 | 7031 | 0.9942 | 7605 | 0.932 | 7.79 |
| 2 | 0.1 | 7031 | 0.9874 | 7605 | 0.898 | 6.96 |
| 2 | 0.2 | 7031 | 0.9719 | 7605 | 0.804 | 5.71 |
| 3 | 0.05 | 7435 | 0.9944 | 7108 | 0.996 | 8.55 |
| 3 | 0.1 | 7435 | 0.9850 | 7108 | 0.981 | 7.92 |
| 3 | 0.2 | 7435 | 0.9667 | 7108 | 0.926 | 6.77 |
| 4 | 0.05 | 5845 | 0.9982 | 7736 | 0.972 | 8.05 |
| 4 | 0.1 | 5845 | 0.9953 | 7736 | 0.926 | 7.51 |
| 4 | 0.2 | 5845 | 0.9787 | 7736 | 0.791 | 5.98 |

## Mean over folds

| α | target 1 − α | coverage | mean set size |
|---|---|---|---|
| 0.05 | 0.95 | 0.951 | 7.78 |
| 0.1 | 0.90 | 0.914 | 7.10 |
| 0.2 | 0.80 | 0.815 | 5.80 |

## Set sizes at α = 0.1 (pooled)

| set size | test images | share |
|---|---|---|
| 1 | 824 | 0.021 |
| 2 | 1089 | 0.028 |
| 3 | 1661 | 0.042 |
| 4 | 2014 | 0.051 |
| 5 | 2790 | 0.071 |
| 6 | 4365 | 0.111 |
| 7 | 5247 | 0.134 |
| 8 | 6607 | 0.168 |
| 9 | 14634 | 0.373 |

## Coverage per cause at α = 0.1 (pooled)

| cause | test images | coverage |
|---|---|---|
| none | 6968 | 0.922 |
| flow_low | 3168 | 0.938 |
| flow_high | 6574 | 0.936 |
| speed_low | 4761 | 0.870 |
| speed_high | 4128 | 0.913 |
| nozzle_temp_low | 1358 | 0.616 |
| nozzle_temp_high | 830 | 0.671 |
| z_offset_low | 1522 | 0.944 |
| z_offset_high | 9922 | 0.955 |

## Runtime qhat

models\cause\qhat.json: qhat = 0.9779 at α = 0.1 from 5657 calibration images of models\cause\preds_final.npz.
