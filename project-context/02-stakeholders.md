<!-- HEAD
FILE:     02-stakeholders.md
PHASE:    1 — UNDERSTAND
UPDATED:  2026-10-03
STATUS:   draft (awaiting gate)
SUMMARY:  Five stakeholders. Dr. Meti renders the verdict and speaks in deck
          vocabulary (envelope, actuation, causality, validation, "explanation
          fidelity"). The SDP examiners measure demo + report. Operators (study
          participants) measure trust and workload. CAIR collaborators measure the
          method choices (conformal, attribution). The REU team owns inherited assets.
OPEN:     Exact SDP rubric (STATE.md Q3).
-->

# Stakeholders

| Stakeholder | Role | What they measure | Their vocabulary | What makes them say no |
|---|---|---|---|---|
| Dr. Vinod Kumar V Meti (CARR) | Guide; verdict owner | Zero constraint violations, explanation fidelity, latency budget kept, operator accuracy | "operating envelope", "actuation within cycle time", "causal ground truth", "explanation-fidelity metric", "recommend-then-act" | Unbounded actions; pixel-only explanations; claims without rig repeatability |
| SDP examiners (KLE Tech) | Grade | Working demo, novelty over seniors, report quality, individual contribution | "objectives", "methodology", "results", "future scope" | Demo fails live; no clear delta over REU work |
| CAIR collaborators | Method partners | Calibration, attribution and counterfactual soundness; transfer protocol | "coverage", "AU-PRO", "calibration", "counterfactual" | Uncalibrated probabilities presented as confidence |
| Printer operators (study participants) | End users | Correct decision, time to decide, workload (NASA-TLX), trust | "what's wrong", "what do I do", "is it safe" | Cards they can't understand in < 30 s |
| REU team (Varshini C Horakeri) | Asset owners | Their results credited and reproduced correctly | mAP50, induction protocol | Misreporting their baseline |
