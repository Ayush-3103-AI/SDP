<!-- HEAD
FILE:     00-charter.md
PHASE:    0 — CHARTER
UPDATED:  2026-10-27
STATUS:   amended (Amendment 2 accepted 2026-10-27, ADR-0009. Amendment 1 superseded)
SUMMARY:  SDP = a UG-scale piece of CARR Topic 4.1.3. It adds an explanation
          layer (cause expressed in process variables, conformal set of causes),
          a 4-layer safety gate and a recommend-then-act operator dashboard to the
          REU 2025-26 YOLO11-S + OctoPrint closed loop on the Ender 5 Plus.
          Success = cause top-1 >= floor+10pp under leave-one-geometry-out, zero
          envelope violations, auto-mode latency p95 <= 0.30 s. Three kill
          criteria. Hybrid project (software + rig + research).
OPEN:     Semester end date, team size, doctrine hook (Q1-Q3 in STATE.md).
-->

# Charter: Explainable, Safe, Human-in-the-Loop Correction for FFF (CARR 4.1.3 slice)

## 1. Problem
The CARR FFF loop (REU 2025-26) detects 7 defect classes and fires **fixed G-code recipes or M112** without saying *why*. It does not:
- bound or scale its corrections;
- ask a human before acting.

Operators therefore can't audit, trust or correct it. In the deck's own words, "Explainable: Absent; Recommendations: Absent; Safe: Partial". This blocks 4.1.3's hypothesis that systems must "infer process-level root causes and generate safe corrective recommendations, with human-in-the-loop validation" (see the `context` file).

## 2. Success metrics (all must be measurable and able to fail)
| # | Metric | Threshold | Conditions |
|---|---|---|---|
| S1 | Cause-explanation top-1 accuracy | ≥ **floor + 10 pp** (floor = majority cause per defect class) | Leave-one-geometry-out (LOGO), mean over folds |
| S2 | Conformal cause-set coverage | ≥ **0.85** at α = 0.10, average set size ≤ **2.0** | LOGO |
| S3 | Safety-envelope violations after the gate | **0** | 100 000 randomised gate cases plus every rig run |
| S4 | Defect → command latency, auto mode | p95 ≤ **0.30 s** (deck baseline 0.21–0.27 s) | Ender 5 Plus, RTX 3050 laptop |
| S5 | Rig correction | Resolution rate ≥ baseline − 5 pp **and** fewer setpoint reversals than the fixed recipes | Induced-defect campaign |

## 3. Kill criteria (stop or pivot when observed)
- **K1:** the data audit finds that < 60 % of defect boxes can be joined to an unambiguous induced cause. Drop the learned cause model and pivot to telemetry + prior-based explanation (ADR-0002 fallback).
- **K2:** LOGO cause top-1 ≤ floor + 5 pp after T-0013. Same pivot.
- **K3:** no working printer + OctoPrint access by week 6. Rig claims (S4, S5) are downgraded to replay + FakePrinter simulation, and the report says so.

## 4. Hard constraints
- **Hardware:**
  - Creality Ender 5 Plus (primary) and Anycubic Kobra 2 Neo, both without firmware modification;
  - Raspberry Pi HQ camera;
  - RTX 3050 laptop with 4 GB VRAM.
- **Inherited stack:**
  - YOLO11-S at 1088 px;
  - OctoPrint REST commands (M104/M220/M221/M140, M112);
  - 6,454-image dataset with induced-cause labels.
- **Team and time:** UG SDP team. The semester end date is unknown; assumed ~14 weeks from 2026-10-03 (STATE.md Q1).
- **Boundary:** must not overlap the PhD topics 4.1.1 (uncertainty in *detection*) or 4.1.2 (*multimodal* root cause). Our uncertainty sits on cause/action, and our inputs are vision plus existing telemetry only.
- **Who does what:** Claude Code writes code. Humans do the printing, data hand-over and the operator study (tickets are tagged CODE / HUMAN / PAIR).

## 5. Project type
Hybrid: software + hardware rig + research evaluation.

## 6. Doctrine hook
Unknown: KLE Tech SDP rubric or CARR lab standards (STATE.md Q3). Until answered, this framework governs.

## Provisional cast
| Role | Skill | Status |
|---|---|---|
| ML training/eval discipline | `ml-model-builder` | [have] |
| Test-first implementation | `mattpocock-skills:tdd` | [have] |
| Final report / paper | `project-report-architect` | [have] |
| Literature refresh if needed | `lit-survey` | [have] |
| FFF process physics / envelope judgement | none | [gap]: handled inline via `07-math.md` + `config/default.yaml`; not built (fails the reuse test for a UG timeline) |

## Amendment 1 (SUPERSEDED by Amendment 2, 2026-10-27) — the REU data does not exist; we generate our own (ADR-0008)
The full REU hand-over is 5,490 unlabelled frames of one print on a different printer. K1 fires for the inherited
data. Instead of the K1 pivot as written (which leaves S1/S2 unmeasurable), we generate cause-labelled data
ourselves. Proposed changes, pending the gate:

| Item | Was | Becomes |
|---|---|---|
| §4 inherited dataset | 6,454 images with induced-cause labels | Own data campaign: 4 geometries × 8 conditions × 2 repeats = 64 recorded trials; ~1,600 box-labelled frames |
| §4 inherited detector | YOLO11-S best.pt | We train YOLO11-S at 1088 px on our labels. AM_1 (1-class YOLOv8n) is used only to pre-annotate |
| S1 | top-1 ≥ floor + 10 pp, LOGO (8 folds) | Same threshold, 4-fold LOGO on own data, mean with bootstrap 95 % CI |
| S2 | coverage ≥ 0.85, set size ≤ 2.0 | Same, on own data, with CI |
| S5 | full induced-defect campaign | Reduced closed-loop campaign, ~16 runs (4 geometries × 4 most frequent causes) |
| S6 (new) | — | Own detector mAP50 ≥ 0.50 on held-out geometries (report-only floor) [assumed] |
| K1 | REU join rate < 60 % → pivot | FIRED for REU data (2026-10-27). Re-evaluated on own data at T-0006; on FAIL → ADR-0002 option 1 |
| K3 | no printer by week 6 | No printer + OctoPrint + fixed camera by week 5 → data campaign impossible; DESCEND again (simulation-only, option 2 in ADR-0008) |
| Safety | all printer commands through gate() | Plus one human-invoked exception: `xqi induce` during data-campaign trials only, operator present, L1 still enforced |

## Amendment 2 (accepted 2026-10-27) — software-only scope (ADR-0009)
User directive: we build only the model software (causability, explainability, proactive human-in-the-loop).
Hardware, printer connection, communication protocol and module choices belong to another team.
- §1 Problem: unchanged in intent. Delivered as software with a Printer-protocol hand-off boundary.
- §2 Success metrics: replaced by ADR-0009 §Metrics:
  - S1/S2 on CAXTON, leave-parts-out
  - S3 software gate
  - S4 offline explanation latency
  - S5 proactive warning (new)
  - S6 counterfactual direction
  - S7 HITL study (SHOULD)
- §3 Kill criteria: K1′ (dataset access), K2 unchanged, K3 dropped.
- §4 Hard constraints:
  - Hardware: RTX 3050 laptop for training/eval only. Ender 5 Plus, Kobra 2 Neo and Pi HQ are out of scope.
  - Inherited stack: replaced by the CAXTON public dataset (licence to confirm) + the inherited models as
    placeholders. OctoPrint becomes the other team's concern.
- §5 Project type: software + research evaluation (no rig).
