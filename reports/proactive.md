NFR-012: FAIL (median 7.4 s, recall 0.01, 0.85 false/h; need ≤ 10 s, ≥ 0.70, ≤ 1 /h; pooled over 5 folds, θ_on from calibration prints)

# Proactive early warning on held-out prints (T-0063)

Predictions: models\cause/preds_fold*.npz, replayed per print in ts order through EarlyWarning (β = 0.8, θ_off = 0.4, m = 3, cooldown 60 s, gap reset 10 s). Onset = a cause entering D(i) at a segment start; a warning is true iff its cause is in D at that image; false warnings in the first 6 s of a segment are not counted; missed = no true warning within 30 s or before the segment ends (07 §14). θ_on is chosen per fold on its calibration prints only; the floor is the same rule with β = 0.

Floor (β = 0): median 6.5 s, recall 0.01, 1.07 false/h.

## θ_on choice (calibration prints only)

| fold | rung | θ_on | false/h | median ttw (s) | recall@30 s | chosen |
|---|---|---|---|---|---|---|
| 0 | ewma | 0.5 | 0.75 | 13.5 | 0.01 | ✔ |
| 0 | ewma | 0.6 | 0.30 | 6.5 | 0.00 |  |
| 0 | ewma | 0.7 | 0.11 | 12.1 | 0.00 |  |
| 0 | ewma | 0.8 | 0.04 | 3.3 | 0.00 |  |
| 0 | floor | 0.5 | 1.05 | 10.9 | 0.01 |  |
| 0 | floor | 0.6 | 0.67 | 13.5 | 0.01 | ✔ |
| 0 | floor | 0.7 | 0.22 | 12.1 | 0.00 |  |
| 0 | floor | 0.8 | 0.04 | 1.4 | 0.00 |  |
| 1 | ewma | 0.5 | 0.88 | 5.1 | 0.01 | ✔ |
| 1 | ewma | 0.6 | 0.29 | 6.5 | 0.00 |  |
| 1 | ewma | 0.7 | 0.17 | 8.1 | 0.00 |  |
| 1 | ewma | 0.8 | 0.04 | 4.2 | 0.00 |  |
| 1 | floor | 0.5 | 1.22 | 8.3 | 0.01 |  |
| 1 | floor | 0.6 | 0.63 | 6.5 | 0.00 | ✔ |
| 1 | floor | 0.7 | 0.29 | 10.2 | 0.00 |  |
| 1 | floor | 0.8 | 0.29 | 5.3 | 0.00 |  |
| 2 | ewma | 0.5 | 0.46 | 2.5 | 0.01 | ✔ |
| 2 | ewma | 0.6 | 0.27 | 2.5 | 0.01 |  |
| 2 | ewma | 0.7 | 0.07 | 5.3 | 0.01 |  |
| 2 | ewma | 0.8 | 0.03 | 4.0 | 0.00 |  |
| 2 | floor | 0.5 | 0.96 | 3.2 | 0.01 | ✔ |
| 2 | floor | 0.6 | 0.76 | 2.8 | 0.01 |  |
| 2 | floor | 0.7 | 0.46 | 2.8 | 0.01 |  |
| 2 | floor | 0.8 | 0.20 | 2.8 | 0.00 |  |
| 3 | ewma | 0.5 | 0.42 | 17.4 | 0.00 | ✔ |
| 3 | ewma | 0.6 | 0.14 | 5.6 | 0.00 |  |
| 3 | ewma | 0.7 | 0.04 | 9.8 | 0.00 |  |
| 3 | ewma | 0.8 | 0.04 | – | 0.00 |  |
| 3 | floor | 0.5 | 0.70 | 9.5 | 0.00 | ✔ |
| 3 | floor | 0.6 | 0.46 | 13.7 | 0.00 |  |
| 3 | floor | 0.7 | 0.28 | 8.8 | 0.00 |  |
| 3 | floor | 0.8 | 0.18 | 29.3 | 0.00 |  |
| 4 | ewma | 0.5 | 1.45 | 8.6 | 0.01 |  |
| 4 | ewma | 0.6 | 0.91 | 6.5 | 0.01 | ✔ |
| 4 | ewma | 0.7 | 0.86 | 9.1 | 0.00 |  |
| 4 | ewma | 0.8 | 0.32 | 6.5 | 0.00 |  |
| 4 | floor | 0.5 | 2.00 | 6.7 | 0.01 |  |
| 4 | floor | 0.6 | 1.41 | 6.5 | 0.01 |  |
| 4 | floor | 0.7 | 0.95 | 9.3 | 0.01 | ✔ |
| 4 | floor | 0.8 | 0.59 | 10.7 | 0.01 |  |

## Test prints per fold (frozen θ_on)

| fold | θ_on | prints | hours | onsets | median ttw (s) | recall@30 s | false/h | β = 0 θ_on | β = 0 median | β = 0 recall | β = 0 false/h |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 0.5 | 28 | 27.34 | 1598 | 7.0 | 0.01 | 0.91 | 0.6 | 3.5 | 0.01 | 0.80 |
| 1 | 0.5 | 67 | 29.03 | 2007 | 12.3 | 0.01 | 1.48 | 0.6 | 12.1 | 0.01 | 1.89 |
| 2 | 0.5 | 28 | 31.44 | 1692 | 7.9 | 0.00 | 0.57 | 0.5 | 4.2 | 0.01 | 1.05 |
| 3 | 0.5 | 29 | 28.28 | 1715 | 6.0 | 0.00 | 0.67 | 0.5 | 3.3 | 0.00 | 0.78 |
| 4 | 0.6 | 29 | 32.22 | 1799 | 6.5 | 0.00 | 0.65 | 0.7 | 2.1 | 0.00 | 0.84 |

## Per cause (pooled test prints)

| cause | onsets | warned | median ttw (s) | recall@30 s | false | false/h | β = 0 median | β = 0 recall | β = 0 false/h |
|---|---|---|---|---|---|---|---|---|---|
| flow_high | 1138 | 13 | 8.4 | 0.01 | 17 | 0.11 | 4.2 | 0.01 | 0.12 |
| flow_low | 1050 | 9 | 11.1 | 0.01 | 24 | 0.16 | 10.7 | 0.01 | 0.17 |
| nozzle_temp_high | 793 | 2 | 3.5 | 0.00 | 17 | 0.11 | – | 0.00 | 0.15 |
| nozzle_temp_low | 1230 | 3 | 25.5 | 0.00 | 17 | 0.11 | 25.1 | 0.00 | 0.10 |
| speed_high | 1075 | 3 | 0.9 | 0.00 | 28 | 0.19 | 10.7 | 0.01 | 0.24 |
| speed_low | 1044 | 6 | 2.6 | 0.01 | 9 | 0.06 | 1.9 | 0.01 | 0.10 |
| z_offset_high | 1425 | 27 | 7.9 | 0.02 | 14 | 0.09 | 6.6 | 0.01 | 0.18 |
| z_offset_low | 1056 | 0 | – | 0.00 | 0 | 0.00 | – | 0.00 | 0.01 |

## Runtime θ_on

θ_on = 0.5 from the calibration prints of models\cause\preds_final.npz (set cfg.proactive.theta_on; the config has 0.6).
