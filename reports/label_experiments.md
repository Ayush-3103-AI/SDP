# CPU label and calibration experiments (2026-11-21)

Dev laptop, CPU only. Test folds are scored once per variant with values fitted on calibration prints; nothing here was
chosen on a test number. Frozen = ImageNet ResNet18 eval-mode features + linear 9-way head (scripts/probe_features.py).

## 1. Post-hoc recalibration of the 11-19 fine-tune (all 79,515 crops, 5 folds, test unchanged)

| preds | top-1 | gap to floor | top-3 | balanced | ECE | conformal set (α 0.1) | report |
|---|---|---|---|---|---|---|---|
| raw (11-19) | 0.209 | −4.5 pp | 0.501 | 0.177 | 0.260 | 7.10 | cause_eval_full.md, conformal.md |
| T only (τ = 0) | 0.209 | −4.5 pp | 0.501 | 0.177 | 0.055 | 7.11 | cause_eval_recal_t.md, conformal_recal_t.md |
| T + prior (τ fitted) | **0.294** | **+4.1 pp** | 0.603 | 0.152 | 0.053 | 6.18 | cause_eval_recal.md, conformal_recal.md |

The prior term lifts top-1 by predicting the majority cause (z_offset_high recall 0.19 → 0.73) while the
actionable-cause recalls collapse (flow_low 0.19 → 0.01, speed_high 0.16 → 0.00). It helps K2, not the operator.
Once probabilities are honest, almost no frame is confident: counterfactual and early-warning events drop to zero
(counterfactual_recal*.md, proactive_recal*.md). The runtime demo uses T only (config/caxton_demo.yaml).

## 2. Label audit (reports/label_audit.md, scripts/clean_labels.py)

- `z_offset_low`: 1,491 of 1,522 single-cause images have z ≤ −1 mm (README: "incorrectly labelled"). 7 survive
  cleaning, so CAXTON cannot teach this class.
- 17.5 % of single-cause frames are inside CAXTON's 15-frame post-change gap.
- 38.5 % of single-cause frames have a setpoint within 5 pp / 3 °C of a class edge (the "good" band is 86–130 %).
- `hotend_class` is cut on the **measured** temperature (195 / 220 °C), not the target: no thermal-lag relabel needed.
- Clean set: 66,664 crops (32,183 single-cause); margin set (train rows only): 40,901 crops.

## 3. Training-label variants, frozen features (19,958 crops: ≤ 120 single-cause per print + 4.6 k earlier)

All three scored on the same clean test rows (13,947 images, 156 prints). Floor = training-print majority.

| train labels | cross-fit calib top-1 − floor | test top-1, argmax (T only) | balanced | test top-1, T + prior | gap |
|---|---|---|---|---|---|
| all | +4.8 pp | 0.226 | 0.172 | 0.335 | +3.2 pp |
| clean | +4.5 pp | 0.246 | 0.184 | 0.337 | +3.4 pp |
| margin | **+6.0 pp** | **0.264** | **0.184** | 0.335 | +3.2 pp |

Cleaning the training labels raises argmax top-1 by 2–4 pp and balanced accuracy by 1.2 pp; after the prior term all
three converge on the floor + ~3 pp. Frozen features stay the ceiling. Nothing on CPU reaches K2 (+5 pp) or NFR-005
(+10 pp): the remaining lever is feature learning on clean labels, which is docs/gpu-runs/SITTING-2026-11-21.md.

Caveats: the subset is ≈ 25 % of the crops, so the variant differences (2–4 pp) are within one fold's std (≈ 5 pp);
read them as direction, not size. The clean test excludes rows the dataset authors call mislabelled; whether K2 is
judged on it is the user's call (DESCEND).
