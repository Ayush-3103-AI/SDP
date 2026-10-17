<!-- HEAD
FILE:     03-landscape.md
PHASE:    1 — UNDERSTAND (compressed: taken from the deck's FA4 survey, ~120 sources)
UPDATED:  2026-10-03
STATUS:   draft (awaiting gate)
SUMMARY:  Detection is saturating; calibrated confidence, a stated safety envelope
          and process-level explanations are rare. Closest analogues are listed.
          CAXTON (Brion & Pattinson 2022) predicts parameter deviations from images
          and is the nearest prior art for our cause model. Failure archaeology: image-level
          splits inflating scores, pixel-heatmap "explanations", unbounded fixed
          recipes, and clog/estop recoverability.
OPEN:     No fresh lit-survey was run; invoke `lit-survey` only if the report's
          related-work section needs more than this.
-->

# Landscape

## Prior art (from the deck unless noted)
- **Detection is mature, trust isn't.** Evidenter AD 2 (2025): state-of-the-art < 60 % AU-PRO under lighting shift / tiny defects. Deep ensembles calibrate better than MC dropout (Pyle et al., 2022).
- **Correction reaching an actuator is rare.**
  - Zhang et al. 2022 (CIRP Annals): in-mould vision → injection moulding.
  - Li et al. 2025: uncertainty-aware RL for extrusion AM, simulation-heavy, no envelope.
  - Senoner et al. 2021: SHAP decision support in semiconductors, −21.7 % yield loss, advisory only.
  - Mo et al. 2025: digital-twin FANUC cell.
- **"Safe" is rarely specified.** Formalisms exist: constraint taxonomies in safe RL, control barrier functions, GP chance constraints. González-Potes et al. 2026: constrained action projection, 6 months with zero violations.
- **Explanations aren't actionable.**
  - XAI in visual QA is dominated by heatmaps.
  - Ahangar et al. 2026 question whether explanations align with physical mechanisms.
  - Senoner et al. 2024: explanations raised inspector accuracy by **+7.7 pp** (pre-registered). This is our study's reference effect size.
- **Not from the deck: CAXTON / Brion & Pattinson, "Generalisable 3D printing error detection and correction via multi-head neural networks", *Nature Communications* 13, 4654 (2022).**
  - Multi-head CNN predicts flow, lateral speed, Z-offset and hotend temperature as low/good/high from images.
  - This is the direct prior art for our cause model (D2). Cite it, and optionally pretrain on it (licence to be checked before use).

## Failure archaeology (what kills projects like this)
| Failure | Signature | Our guard |
|---|---|---|
| Image-level random split on video-derived frames | Val ≫ field accuracy; near-identical frames on both sides | Split by trial, LOGO (ADR-0007) |
| Setpoint leakage into a "cause" model | ~100 % cause accuracy | Image + class only (ADR-0002); T-0013 sanity check |
| Heatmap-as-explanation | Pretty overlays, nothing an engineer can act on | Explanation = process variable + direction + bounded Δ |
| Fixed absolute recipes | Oscillation, overshoot, stacking corrections | L2 step + cooldown + severity scaling |
| M112 for recoverable faults | Every clog kills the print; reboot needed | ADR-0006 option to pause |
| Human-in-the-loop that waits forever | Defect propagates while the card is unanswered | Response timeout with configured default (FR-019) |
| Conformal guarantee claimed under distribution shift | Coverage reported as guaranteed on a new geometry | Report *empirical* LOGO coverage; guarantee stated only for exchangeable data |
