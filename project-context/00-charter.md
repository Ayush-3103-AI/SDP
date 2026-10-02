<!-- HEAD
FILE:     00-charter.md
PHASE:    0 — CHARTER
UPDATED:  2026-10-03
STATUS:   draft (awaiting gate)
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
