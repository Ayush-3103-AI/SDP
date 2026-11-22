# Post-hoc recalibration on calibration prints (2026-11-21)

Source: models/cause/v2/a3/preds_*.npz. q = softmax(log p / T + τ·log π̂), (T, τ) by calib NLL; π̂ = calib label frequencies. Test rows are transformed with these calib-fitted values only (no test choice). Cross-fit = fit on half the calib prints, score the other half: the recipe-comparison score. Window = causal mean log-prob of the last k frames (k by calib NLL), report only.

| preds | T | τ | calib NLL | calib ECE | calib top-1 | calib balanced | calib floor | cross-fit top-1 (− floor) | cross-fit balanced | window k | window calib top-1 | window test top-1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| fold0 | 4.59 | 0.750 | 2.038 → 1.953 | 0.049 → 0.003 | 0.243 → 0.240 | 0.154 → 0.126 | 0.238 | 0.239 (+0.0 pp) | 0.125 | 15 | 0.239 | 0.199 |
| fold1 | 1.87 | 0.500 | 1.836 → 1.790 | 0.058 → 0.030 | 0.334 → 0.345 | 0.195 → 0.181 | 0.264 | 0.258 (+9.0 pp) | 0.132 | 15 | 0.368 | 0.359 |

Mean cross-fit top-1 − floor over 2 folds: +4.5 pp; balanced 0.129.
