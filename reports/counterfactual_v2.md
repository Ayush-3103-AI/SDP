NFR-007: FAIL (direction fidelity 0.000 on 0 confident events, need ≥ 0.85; confident fraction 0.000 of 17962 actionable test images; pooled over 5 folds)

# Counterfactual direction fidelity on confident events (T-0017)

Predictions: models\cause\v2\a1\recal_t/preds_fold*.npz. Confident = |C| = 1, C ≠ {none}, p_top ≥ τ = 0.6 (L4 would pass), qhat per fold at α = 0.1 from its calibration prints. Fidelity = the top-1 proposal changes the true cause's variable in the undoing direction. Actionable true causes only; none, manual (z_offset) and multi images are excluded.

## Per fold

| fold | qhat | actionable | confident | confident fraction | fidelity |
|---|---|---|---|---|---|
| 0 | 0.9239 | 3965 | 0 | 0.000 | – |
| 1 | 0.9311 | 3296 | 0 | 0.000 | – |
| 2 | 0.9288 | 3765 | 0 | 0.000 | – |
| 3 | 0.9362 | 3576 | 0 | 0.000 | – |
| 4 | 0.9351 | 3360 | 0 | 0.000 | – |

## Per cause (pooled)

| cause | var | actionable | confident | confident fraction | fidelity | median abs logged deviation |
|---|---|---|---|---|---|---|
| flow_low | flow | 2725 | 0 | 0.000 | – | 58 % |
| flow_high | flow | 5683 | 0 | 0.000 | – | 63 % |
| speed_low | speed | 4121 | 0 | 0.000 | – | 53 % |
| speed_high | speed | 3503 | 0 | 0.000 | – | 61 % |
| nozzle_temp_low | nozzle_temp | 1209 | 0 | 0.000 | – | 16 °C |
| nozzle_temp_high | nozzle_temp | 721 | 0 | 0.000 | – | 17 °C |

Steps-to-undo (07 §9) is not computed: CAXTON's deviation magnitudes vary within a cause, so the median |logged deviation| from the good-class median stands in for it.
