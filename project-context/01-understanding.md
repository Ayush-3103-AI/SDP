<!-- HEAD
FILE:     01-understanding.md
PHASE:    1 — UNDERSTAND (compressed; derived from the deck + 2026-10-03 planning chat)
UPDATED:  2026-10-03
STATUS:   draft (awaiting gate)
SUMMARY:  12 settled decisions (standalone package; image-only learned cause model;
          split-conformal cause sets; pure-function 4-layer gate that clips at L2
          and rejects at L1/L3; Streamlit+SQLite HITL; 4 run modes for A/B;
          explanation off the critical latency path except the cause model).
          11 assumptions, 4 of them [unknown]; A1 (cause labels are joinable to
          boxes) and A3 (cause is learnable from the image) are the project-killers
          and are attacked first.
OPEN:     B1-B4 (open branches below).
-->

# Understanding

## Inherited system (verified only from the deck, not yet from code)
Pipeline:
1. Camera (Pi HQ, 1920×1056) → YOLO11-S (1088 px, 7 classes + no-defect; 32–36 ms).
2. Per-class confirmation over 2–4 consecutive hits.
3. Critical defects (clog, layer shift, spaghetti) → **M112**.
4. Otherwise → fixed recipe via OctoPrint.

Measured: mAP50 0.809 val / 0.828 test, defect → command 0.21–0.27 s.

Inherited recipes (deck):

| Defect | Commands |
|---|---|
| over-extrusion | `M104 S190, M220 S95, M221 S80` |
| under-extrusion | `M104 S205, M220 S80, M221 S110` |
| stringing | `M104 S190, M220 S80, M221 S95` |
| warping | `M140 S65` |

The `AM_1_Model_1.pt` / `AM_2_Model_2.pt` files in the repo root are **older YOLOv8n iterations**, not this system. Do not build on them.

## Settled decisions
| # | Decision | Choice | Rationale | Reversibility |
|---|---|---|---|---|
| D1 | Codebase | New standalone package `xqi/` that reimplements the thin loop. REU code is reference only. | REU code unseen; the loop is ~150 lines; owning it lets us A/B the modes | cheap (ADR-0001) |
| D2 | What the explanation predicts | One label per confirmed defect, chosen from a fixed set of **joint causes** (`flow_low`, `nozzle_temp_high`, …) | Deck demands "process variables, not pixel heatmaps"; induced causes give ground truth | costly (ADR-0002) |
| D3 | Inputs to the learned model | Defect **crop + defect class only**. Commanded setpoints and telemetry are **never** model inputs. | Defects were induced by commanding setpoints → leakage would fake accuracy | one-way for the eval's validity (ADR-0002) |
| D4 | Uncertainty | Split conformal (LAC) → set of causes at risk α | Deck's own suggestion; the set *is* the "range of solutions" | cheap (ADR-0003) |
| D5 | Safety | Pure function `gate()`, 4 layers. L1/L3 reject, L2 clips, L4 routes to auto vs human. Fails closed. | Deck's four-layer proposal; pure = property-testable | costly (ADR-0004) |
| D6 | Human in the loop | Streamlit dashboard + SQLite event store (WAL); loop and UI are separate processes | Fastest UI for a UG team; SQLite gives a free audit log | cheap (ADR-0005) |
| D7 | Critical classes | Configurable; default = deck behaviour (M112). Clog → pause is offered as an option pending Dr. Meti | Don't silently change safety behaviour | cheap (ADR-0006) |
| D8 | Primary eval split | Leave-one-geometry-out over 8 geometries, split **by trial**, never by image | Near-duplicate frames inside a trial inflate scores | one-way once results are seen (ADR-0007) |
| D9 | Run modes | `baseline` (deck recipes, no gate), `gated-recipe`, `auto`, `advisory` | Every claim needs a same-rig comparison | cheap |
| D10 | Latency path | Action path = detect → confirm → cause model → conformal → gate → send. Heatmap (EigenCAM) runs **after** sending. | Protect the 0.21–0.27 s budget | cheap |
| D11 | Correction magnitude | Δ scaled by defect severity between d_min and d_max (≤ L2 step); repeated cycles accumulate under cooldown | Deck gap "not scaled to magnitude" | cheap |
| D12 | Counterfactual | Smallest in-envelope setpoint change that undoes the predicted cause. Validated offline by direction fidelity and on the rig by outcome. No image-generative counterfactuals. | Measurable with induced ground truth; generative CF out of UG scope | cheap |

## Open branches
- **B1** Final cause taxonomy and cause→defect map. Settled in T-0007 after the data audit.
- **B2** Envelope numbers (L1/L2 from printer spec; L3 from trial data + Dr. Meti). Settled in T-0024/T-0025.
- **B3** Clog → M112 or pause. Dr. Meti decides; default M112.
- **B4** Leave-one-printer-out (Kobra 2 Neo) transfer. COULD, T-0050.

## Assumptions
| ID | Assumption | Tag | Retired by |
|---|---|---|---|
| A1 | The induction log can be joined to images so that ≥ 60 % of defect boxes get one unambiguous cause | [unknown] | T-0005, T-0006 (K1) |
| A2 | REU YOLO11-S weights + test split reproduce mAP50 ≈ 0.828 | [assumed] | T-0008 |
| A3 | The cause is learnable from a defect crop beyond the majority-per-class floor | [unknown] | T-0012, T-0013 (K2) |
| A4 | OctoPrint reachable; temps readable; dispatch 20–40 ms | [assumed] | T-0028 |
| A5 | Ender 5 Plus hotend is PTFE-lined → nozzle L1 max 240 °C | [assumed] | T-0025 (human) |
| A6 | Cause model + conformal + gate add ≤ 30 ms p95 on the RTX 3050 | [assumed] | T-0036 |
| A7 | REU test split was image-level random (possible near-duplicate leakage) | [unknown] | T-0008 report notes it |
| A8 | Each trial induces one cause at a time (or co-occurrence is labelled) | [unknown] | T-0006 |
| A9 | Marlin accepts M220/M221 via OctoPrint mid-print without side effects | [assumed]: deck uses them | T-0028 |
| A10 | Operators can be recruited (8–12) for a 30-min study | [assumed] | T-0045 |
| A11 | Flow/speed overrides can't be read back over OctoPrint → tracked locally | [assumed] | T-0027 |
