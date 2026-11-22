# Post-hoc recalibration on calibration prints (2026-11-21)

Source: models/cause/v2/a2/preds_*.npz. q = softmax(log p / T + τ·log π̂), (T, τ) by calib NLL; π̂ = calib label frequencies. Test rows are transformed with these calib-fitted values only (no test choice). Cross-fit = fit on half the calib prints, score the other half: the recipe-comparison score. Window = causal mean log-prob of the last k frames (k by calib NLL), report only.

| preds | T | τ | calib NLL | calib ECE | calib top-1 | calib balanced | calib floor | cross-fit top-1 (− floor) | cross-fit balanced | window k | window calib top-1 | window test top-1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| fold0 | 2.64 | 0.500 | 2.011 → 1.929 | 0.093 → 0.008 | 0.265 → 0.259 | 0.167 → 0.144 | 0.238 | 0.254 (+1.6 pp) | 0.140 | 15 | 0.260 | 0.283 |
| fold1 | 1.87 | 0.500 | 1.823 → 1.773 | 0.074 → 0.052 | 0.350 → 0.350 | 0.197 → 0.183 | 0.264 | 0.244 (+7.7 pp) | 0.124 | 15 | 0.380 | 0.363 |

Mean cross-fit top-1 − floor over 2 folds: +4.6 pp; balanced 0.132.
