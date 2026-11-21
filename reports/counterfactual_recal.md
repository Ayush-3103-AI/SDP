NFR-007: FAIL (direction fidelity 0.000 on 0 confident events, need ≥ 0.85; confident fraction 0.000 of 20819 actionable test images; pooled over 5 folds)

# Counterfactual direction fidelity on confident events (T-0017)

Predictions: models/cause/recal/preds_fold*.npz. Confident = |C| = 1, C ≠ {none}, p_top ≥ τ = 0.6 (L4 would pass), qhat per fold at α = 0.1 from its calibration prints. Fidelity = the top-1 proposal changes the true cause's variable in the undoing direction. Actionable true causes only; none, manual (z_offset) and multi images are excluded.

## Per fold

| fold | qhat | actionable | confident | confident fraction | fidelity |
|---|---|---|---|---|---|
| 0 | 0.9373 | 4594 | 0 | 0.000 | – |
| 1 | 0.9464 | 3868 | 0 | 0.000 | – |
| 2 | 0.9328 | 4348 | 0 | 0.000 | – |
| 3 | 0.9543 | 4075 | 0 | 0.000 | – |
| 4 | 0.9476 | 3934 | 0 | 0.000 | – |

## Per cause (pooled)

| cause | var | actionable | confident | confident fraction | fidelity | median abs logged deviation |
|---|---|---|---|---|---|---|
| flow_low | flow | 3168 | 0 | 0.000 | – | 58 % |
| flow_high | flow | 6574 | 0 | 0.000 | – | 63 % |
| speed_low | speed | 4761 | 0 | 0.000 | – | 52 % |
| speed_high | speed | 4128 | 0 | 0.000 | – | 61 % |
| nozzle_temp_low | nozzle_temp | 1358 | 0 | 0.000 | – | 15 °C |
| nozzle_temp_high | nozzle_temp | 830 | 0 | 0.000 | – | 18 °C |

Steps-to-undo (07 §9) is not computed: CAXTON's deviation magnitudes vary within a cause, so the median |logged deviation| from the good-class median stands in for it.
