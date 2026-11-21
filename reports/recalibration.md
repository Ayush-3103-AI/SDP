# Post-hoc recalibration on calibration prints (2026-11-21)

Source: models/cause/preds_*.npz. q = softmax(log p / T + τ·log π̂), (T, τ) by calib NLL; π̂ = calib label frequencies. Test rows are transformed with these calib-fitted values only (no test choice). Cross-fit = fit on half the calib prints, score the other half: the recipe-comparison score. Window = causal mean log-prob of the last k frames (k by calib NLL), report only.

| preds | T | τ | calib NLL | calib ECE | calib top-1 | calib balanced | calib floor | cross-fit top-1 (− floor) | cross-fit balanced | window k | window calib top-1 | window test top-1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| final | 4.92 | 1.000 | 2.406 → 1.801 | 0.195 → 0.069 | 0.179 → 0.310 | 0.141 → 0.156 | 0.265 | 0.301 (+3.6 pp) | 0.149 | 15 | 0.318 | – |
| fold0 | 4.00 | 0.750 | 2.370 → 2.001 | 0.173 → 0.033 | 0.250 → 0.261 | 0.203 → 0.139 | 0.221 | 0.250 (+2.9 pp) | 0.136 | 15 | 0.258 | 0.310 |
| fold1 | 2.83 | 0.750 | 2.176 → 1.756 | 0.244 → 0.049 | 0.322 → 0.371 | 0.274 → 0.200 | 0.247 | 0.333 (+17.3 pp) | 0.182 | 15 | 0.378 | 0.308 |
| fold2 | 4.00 | 0.750 | 2.365 → 1.892 | 0.233 → 0.044 | 0.233 → 0.312 | 0.209 → 0.137 | 0.293 | 0.310 (+1.7 pp) | 0.135 | 15 | 0.311 | 0.251 |
| fold3 | 5.66 | 1.000 | 2.570 → 1.996 | 0.204 → 0.061 | 0.178 → 0.288 | 0.151 → 0.153 | 0.233 | 0.272 (+7.5 pp) | 0.148 | 15 | 0.299 | 0.361 |
| fold4 | 6.06 | 0.875 | 2.671 → 1.908 | 0.251 → 0.024 | 0.200 → 0.271 | 0.161 → 0.145 | 0.229 | 0.238 (+5.6 pp) | 0.130 | 15 | 0.295 | 0.270 |

Mean cross-fit top-1 − floor over 5 folds: +7.0 pp; balanced 0.146.
