# Cause identification beyond "one more image classifier": causal, multimodal, measurement-based and defect-first approaches

Scope: options the team could pivot to after the image-only 9-way ResNet18 cause model failed on held-out prints (top-1 0.209 vs majority floor 0.254; random-image split 0.43 balanced acc vs 0.21 held-out-print). It does not repeat CAXTON, domain generalisation, Grad-CAM, conformal or CUSUM work (see `research_notes/FFF cause model build plan/`).

Labels: **[VERIFIED at source]** means the claim was read in the paper text or abstract page. **[snippet-inferred]** means it comes from search snippets or secondary pages only. Maturity: **Consensus / Emerging / Speculative**. Fit (1–10) is for a software-only team with public CAXTON (images plus logged setpoints, no extra sensors) and a 4 GB GPU laptop.

Split types matter most here. "Random" means a random image or sample split, where frames from the same print sit in both train and test. "Held-out part" means whole parts or prints are excluded from training.

---

## 1. Causal inference and root-cause analysis in manufacturing and AM

### Takeaway
No paper was found that runs data-driven causal discovery (PC, FCI, NOTEARS) on FFF process data to identify defect causes. Causal work in AM is either expert-built (DEMATEL, FMEA, ontologies, hand-built Bayesian networks) or, outside AM, structure learning on observational production-line data. **CAXTON is an interventional dataset.** Its setpoints were commanded by script, so the causal direction (setpoint → deposition appearance) is known by design and there are no confounders among the parameters to discover. Running causal discovery on CAXTON would only rediscover the experiment design. The real causal task is **abduction**: given an observed effect, infer which intervention produced it. That is Bayesian inversion, not graph discovery.

### Cited findings
- **Bacha, Sabry & Benhra, "Fault Diagnosis in the Field of Additive Manufacturing (3D Printing) Using Bayesian Networks", iJOE 15(3), 2019**, doi 10.3991/ijoe.v15i03.9375 — [page](https://online-journals.org/index.php/i-joe/article/view/9375). The BN is built from sensor data ("some of these sensors are already available in most of the 3d printers … while other sensors were additionally embedded"). The abstract claims "a high level of fault diagnosis accuracy" but gives no numbers, no split and no network structure. [VERIFIED at source: abstract only]. Emerging/weak. Fit 3: it needs sensors the team lacks.
- **Marazopoulou, Ghosh, Lade & Jensen, "Causal Discovery for Manufacturing Domains", arXiv 1605.04056, 2016** — [arXiv](https://arxiv.org/abs/1605.04056). Causal structure learning on observational assembly-line data to find factors that affect yield. Validated by structure-learning metrics and expert review ("found them promising"). No accuracy, no held-out evaluation. [VERIFIED at source: abstract]. Emerging. Fit 2: it solves an observational-confounding problem that CAXTON does not have.
- **Mokhtarian et al., CIRP CMS 2019** — converts an expert cause–effect model into a Bayesian network that predicts defects from process parameters and reasons backwards to the required inputs — [trepo.tuni.fi PDF](https://trepo.tuni.fi/bitstream/10024/129531/1/2019_CIRP_CMS_Conference_1.pdf). [snippet-inferred]. Emerging. Fit 5 as a *pattern* for an expert-prior BN.
- **Expert causal maps of AM defects:** DEMATEL over AM defects (*Sustainability* 17(18):8498, 2025, [MDPI](https://www.mdpi.com/2071-1050/17/18/8498)) and the FMEA causal chain for L-PBF (Muller, Quinsat & Tournier, *IJPR* 2024, [IDEAS](https://ideas.repec.org/a/taf/tprsxx/v62y2024i23p8443-8461.html)). Both use expert judgement and no learned structure. [snippet-inferred]. Emerging.
- **Wang & Cheung, knowledge-graph embedding for AM defect diagnosis, *Computers in Industry* 2023** — a literature-derived ontology and triples (parameter–effect–defect–quality) with a relational GCN that infers hidden links — [PolyU](https://research.polyu.edu.hk/en/publications/knowledge-graph-embedding-learning-system-for-defect-diagnosis-in/). It is not FFF-specific and was not evaluated on images. [snippet-inferred]. Emerging. Fit 4.
- **CausalTrace (arXiv 2510.12033, 2025)** — an agent for causal discovery, RCA and counterfactuals in smart manufacturing — [arXiv](https://arxiv.org/pdf/2510.12033v1). [snippet-inferred]. Speculative for FFF.

### Inferences
- An **expert-prior Bayesian layer** (defect → candidate causes, with priors and likelihoods) is the useful part of this literature. Learned causal graphs are not.
- **Counterfactual reasoning is cheap here because the forward direction is labelled.** A *forward* model f(setpoints) → expected appearance features can be fitted from CAXTON. Setpoints are a legitimate input to a forward model and do not violate ADR-0002, which constrains only the inverse cause model. "What if flow +10 %" then becomes a query on f.

### Gaps
- No FFF paper reports cause-identification accuracy from a Bayesian network or a structural causal model on held-out prints.

---

## 2. Multimodal and sensor-based cause identification in FFF; what reopening ADR-0002 would mean

### Takeaway
Sensor-based FFF monitoring (acoustic emission, vibration, motor current, thermal, heterogeneous fusion) is mature for **machine-state faults** such as clogs, filament breakage, runout, jams and warpage. No paper found reports cause-identification accuracy on **held-out parts or prints**. Most use random window splits or a single part, or report no split at all. CAXTON has none of these sensors. **The literature gives no support for reopening ADR-0002 with CAXTON.**

### Cited findings
- **Acoustic emission (AE).** Yang et al., filament breakage by AE, *Sensors* 2018 ([PMC](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5877116/)). Liu et al., unsupervised clustering of extruder states from AE, *J. Manuf. Proc.* 2018. Xu, Lyu & Manoochehri 2022, AE plus laser scan with SVM, NB and DT for warpage ([Stevens](https://researchwith.stevens.edu/en/publications/in-situ-process-monitoring-using-acoustic-emission-and-laser-scan/)). A Stevens study classifies jamming and breakage with supervised AE ([Stevens](https://researchwith.stevens.edu/en/publications/detection-of-jamming-and-filament-breakage-in-fdm-using-vibration/)). [snippet-inferred]. These are small lab rigs. No held-out-part numbers were seen. Consensus for machine-state faults. Fit 1 (no sensor).
- **Motor current and vibration for clogs.** Tlegenov, Hong & Lu, accelerometer on the extruder bar mount, *RCIM* 2018. Tlegenov, Wong & Hong, beam model of the liquefier mount, *RPJ* 2017. Current-based nozzle condition monitoring, *Prog. Addit. Manuf.* 2019, doi 10.1007/s40964-019-00089-3 ([Springer](https://link.springer.com/article/10.1007/s40964-019-00089-3), [Cambridge repo](https://www.repository.cam.ac.uk/handle/1810/294250)). Physics-model based. [snippet-inferred]. Consensus for clogs. Fit 1.
- **Waheed, Bernadin & Hassan, "Advancing Industry 4.0: Multimodal Sensor Fusion for AI-Based Fault Detection in 3D Printing", arXiv 2602.16108 (IJERI 2025)** — acoustic, vibration and thermal spectrograms classified with a CNN for clogging, runout and misalignment. The abstract gives **no accuracy, dataset size or split** — [arXiv](https://arxiv.org/abs/2602.16108). The companion arXiv 2602.16119 reports no classifier and no accuracy. [VERIFIED at source: abstracts]. Emerging. Fit 1.
- **Heterogeneous-sensor FFF (Liu / Rao group, Virginia Tech)** — thermocouples, accelerometers, IR and a borescope with a Dirichlet-process mixture plus evidence theory. It reports ~85 % average F-score for failure detection — [VT dissertation](https://vtechworks.lib.vt.edu/handle/10919/78722), [scite](https://scite.ai/authors/jia-liu-OjbN2j). [snippet-inferred]: venue and split were not confirmed. Emerging.
- **Image plus numeric-parameter fusion (SAE 2026-01-0140)** — IR images with infill pattern and nozzle temperature as inputs predict *mechanical performance*. It claims fusion beats single-source models, and mentions no held-out evaluation — [SAE](https://saemobilus.sae.org/papers/a-framework-predicting-mechanical-performance-fff-printed-parts-using-multimodal-deep-learning-infrared-images-2026-01-0140). [snippet-inferred]. This is the clearest example of setpoints as *inputs*, but the target is the part property, not "which setpoint is wrong".
- **CIPHER (Margadji & Pattinson, arXiv 2506.08462, 2025)** — the regression "process expert" is a ResNet-152 trained on >1 M nozzle images labelled from firmware flow. Its metrics come from "1,000 held-out test samples", a **random sample split, not split by part**. MAE is 82.92 without the expert and 17.52 with it. Accuracy 88.25 ± 1.46 (bucketed). — [arXiv html](https://arxiv.org/html/2506.08462v1). [VERIFIED at source].

### What information leakage means here (precise)
In CAXTON the **label is the commanded setpoint**: `flow_rate` (M221), `feed_rate` (M220), `z_offset` and `target_hotend`. Deployed faults are *physical disturbances*: a partial clog, wet or undersized filament, a drifting thermistor, a mis-levelled bed. During those, the commanded setpoints stay at nominal. Any input whose value is a function of the *commanded* setpoint therefore gives the model the answer during training and test, and gives it nothing in deployment:
- `flow_rate`, `feed_rate`, `z_offset`, `target_hotend` → the label itself. Direct leakage.
- `hotend` (measured) tracks `target_hotend` within seconds → leaks the nozzle_temp± label. Its transient also marks *when* a change was commanded, which leaks change-point timing for every head.
- `print_id`, `timestamp`, `img_num` → per-print identity and position in the schedule. This is the same per-print shortcut that inflated the random split.
- A telemetry signal is legitimate only if it measures the **physical response** to the disturbance rather than the command, *and* the training data contain disturbances that were not commanded. Examples: extruder motor current or back-pressure, or a filament-feed encoder comparing actual vs commanded filament. CAXTON has neither.
- A cheap audit for any proposed input x: train a probe x → label. If the probe is near-perfect on CAXTON but x would be constant (nominal) under a real fault, x leaks.

### Inferences (ADR-0002 verdict)
- **Keep ADR-0002 closed for CAXTON.** A fused image plus telemetry model would show high held-out accuracy that is entirely leakage.
- A reopen is defensible only with a new dataset of *physical* faults (induced clog, wrong filament diameter, thermistor offset) and response sensors. That is outside a software-only team's scope.
- Setpoints may still be used legitimately: (a) as inputs to a **forward** model (§1, §5), (b) for evaluation and labels, (c) as *nominal context* (the slicer plan) only when the plan does not vary with the label. In CAXTON it does vary, so (c) is not available.

### Gaps
- No paper found reports leave-one-print-out or leave-one-part-out accuracy for sensor-based FFF *cause* identification.

---

## 3. Physics-informed and measurement-based approaches (bead width, flow regression, reference frames)

### Takeaway
The strongest primary evidence in this survey: **Margadji, Brion & Pattinson 2024 report that continuous flow regression also collapses on unseen parts, from 12.31 to 38.24 MAE (~3.1×).** Their remedy was **per-part calibration** with a few labelled calibration builds, not a better architecture. Switching from classification to regression alone will not fix the held-out-print gap. Geometric measurement (bead width) and comparison against a reference are more physically grounded. They are validated for *measurement accuracy*, but nobody has reported cross-part *cause* accuracy for them.

### Cited findings
- **Margadji, Brion & Pattinson, "Iterative learning for efficient additive mass production", *Additive Manufacturing* 89 (2024) 104271**, doi 10.1016/j.addma.2024.104271 — [PDF](https://cemag1.github.io/assets/papers/Iterative_learning%20for_efficient_additive_mass_production.pdf). [VERIFIED at source: full text]
  - Model: RegNet regression of flow rate from the nozzle-camera image. Targets in log space (30–300 % → −1…+1). 60 parts (40 3D, 20 2D), 1,120,120 images, "random sampling approach … 80:10:10" split (**random split**).
  - "MAE on the held-out test set was observed to be 12.31" (flow-% units). Then: "a steep decline in performance was observed during inference on data from unseen parts that have been totally excluded from the training set … deterioration to 38.24 MAE units". GradCAM++ suggests the model attends to "previously unseen geometric features … rather than critical regions such as the most recent extrusion". This is the same failure as SDP's per-print appearance shortcut.
  - Fix: fine-tune the last 6 sub-blocks on 1, 5 or 10 "calibration parts" (the target part printed with deliberate flow errors). MAE fell by 8.64, 10.05 and 12.53 over 15 test geometries. Cross-printer test (Lulzbot Taz-6, 0.6 mm nozzle, ABS): MAE 69.21 → 19.68 after 10 calibration parts.
  - Iterative learning (machine-in-the-loop labels from firmware plus particle-filter belief) went from 70.13 % → 182.31 % → 91.22 % → 101.20 % ± 5.55 average flow on part P08 over 10 iterations. Ablation: RegNetX_400MF (2.1 M params, 9.34 ms/frame on CPU) gave MAE 19.21. The 4 GB budget fits easily.
  - Maturity: Emerging (one group, strong). Fit 7.
- **Fast-CAXTON (Brion & Pattinson, *Adv. Intell. Syst.* 2022)** — flow regression with RegNet at ~15 Hz. Already covered in `caxton_and_literature.md` Q3. The Wiley page returned 403, so its split was **not verified**. The Margadji 2024 numbers above are the best available held-out-part evidence for this model family.
- **Shabani & Martinez-Hernandez, "In-Situ Measurement of Extrusion Width for FFF Using Vision and Machine Learning Models", IROS 2023** — camera in a printable shroud, two-stage segmentation (best: FCN segmentation + YOLO localisation), "can measure sub-millimeter extrusion width with 90 μm accuracy at 125 ms speed". No generalisation test — [Bath portal](https://researchportal.bath.ac.uk/en/publications/in-situ-measurement-of-extrusion-width-for-fused-filament-fabrica/). [VERIFIED at source: abstract]. Emerging. Fit 4: CAXTON has no width labels and its nozzle-crop view is oblique.
- **Badarinath et al. (Penn State)**, microscope camera with REXR edge detection. Width within 0.08 mm of calipers. Converted to a volumetric flow estimate, and a later version is 6× faster — [PSU](https://pure.psu.edu/en/publications/real-time-vision-sensor-for-volumetric-flowrate-estimation-in-rob/). [snippet-inferred]. Emerging.
- **Lin, Guidetti, Nagel, Balta & Lygeros, "One-Shot Camera-Based Extrusion Optimization for High Speed FFF", arXiv 2512.24905, 2025** — two printed test patterns photographed with a phone identify extrusion dynamics. A model-based constrained optimal controller rewrites the G-code, giving "surface quality at 3600 mm/min comparable to conventional printing at 1600 mm/min". No learning — [arXiv](https://arxiv.org/abs/2512.24905). [VERIFIED at source: abstract]. Emerging. Fit 2: it needs printing.
- **Reference and golden-frame comparison.** Petsiuk & Pearce, layer images vs **G-code-rendered synthetic references**, 12 similarity measures over 6 failure types — [arXiv 2111.02703](https://www.arxiv.org/pdf/2111.02703). They say themselves it is not a full correction algorithm. Niu et al., **Semi-Siamese change detection** (reference schematic vs camera image), F1 > 0.9, robust to camera angle and lighting, demonstrated on binder jet — [arXiv 2212.08583](https://arxiv.org/abs/2212.08583v2). [snippet-inferred]. Emerging.

### Inferences
- The diagnosed failure (per-print appearance dominates) is exactly what a **reference-conditioned** model is built to remove. The input is (current crop, reference crop from the *same print* at known-good settings), or a feature difference. Physically, a cause is a *change* in the bead relative to that print's own normal, not an absolute look.
- Deployment equivalent: the first N seconds of a print (or a calibration patch) are taken as the reference. No setpoint is read at inference.
- **To check before building:** whether every CAXTON print has an early nominal segment (flow and feed 100 %, nominal temperature and z). If prints start off-nominal, the reference must be chosen *without* labels (for example, the earliest frames), and the evaluation must state that rule.
- Per-print calibration (Margadji's recipe) is the empirically proven fix, but it needs labelled calibration frames from the target print. On CAXTON this can be emulated: fine-tune on the first k % of a held-out print's frames and test on the rest, keeping them temporally disjoint. **This changes the evaluation protocol, so it needs user approval and must not touch the `logo.json` test folds for tuning.**

### Gaps
- No paper compares classification vs regression vs reference-conditioned models under the *same* held-out-part protocol.

---

## 4. Defect first, then defect → cause with priors

### Takeaway
Detecting the visible defect and then mapping defect → candidate causes is what practitioners and the newest LLM/VLM systems do (LLM-3D Print, CIPHER). It also matches SDP's objective directly ("what went wrong" + "ranked fixes"). The physics supports it: several of the 9 causes produce the *same* visible symptom, so a 9-way cause label is partly **unidentifiable** from one nozzle crop, while the symptom (under/over-extrusion and its severity) is identifiable. **No head-to-head study was found showing that defect detection generalises across parts better than cause classification.** Treat that as a hypothesis the team can test on CAXTON cheaply.

### Cited findings
- **Jadhav, Pak & Barati Farimani, "LLM-3D Print: Large Language Models To Monitor and Control 3D Printing", arXiv 2408.14307 (v3 2025)** — [arXiv html](https://arxiv.org/html/2408.14307v3). [VERIFIED at source]
  - GPT-4o looks at per-layer top and front images, names the defect, queries printer state over the Moonraker API, and proposes and applies fixes (temperature, speed, flow, fan, pressure advance, retraction, Z-offset). "Defect → cause" is done by LLM reasoning (stringing → retraction, under-extrusion → flow).
  - Evaluation is mostly qualitative. Under-extrusion fixed "within about 5 iterations" on 4 geometries (Ender 3). Compression peak-load gains of 1.34–5.06×. 14-engineer comparison as confusion matrices with no P/R in the text. No held-out split concept. "processing a single layer takes between 15 to 45 seconds".
  - Failure modes: it conflates blobs with stringing, misattributes minor warping, and is inconsistent on subtle layer separation.
  - Emerging. Fit 3: cloud API, per-layer pause, wrong camera view for CAXTON.
- **CIPHER (Margadji & Pattinson 2025)** (see §2) — a regression perception expert conditions a Llama-3.2-11B VLM. RAG over 3,930 facts produces chain-of-thought explanations and actions. Decision accuracy is not reported; OOD claims are qualitative. [VERIFIED at source]. Speculative for SDP. Fit 2: an 11B VLM does not fit 4 GB.
- **Brion, Shen & Pattinson, warp recognition and correction, *Additive Manufacturing* 2023** — a YOLOv3 defect detector (~10k images, ~1.4k warp) plus **expert heuristics** map warp severity → bed temperature and other settings. The detect-then-heuristic pattern — [matta.ai](https://www.matta.ai/research/automated-recognition-and-correction-of-warp-deformation), [Cambridge repo](https://www.repository.cam.ac.uk/handle/1810/336241). [snippet-inferred]. Unseen-part precision was not confirmed. Emerging.
- **Kang & Kim, Keyword-RAG over a 3D-printing troubleshooting guide, *JCDE* 2026** — context recall 0.728, precision 0.599, better than naive RAG — [OUP](https://academic.oup.com/jcde/article/13/6/68/8696400). [snippet-inferred]. This is a source for defect → cause priors.
- Random-split defect classifiers report 98–99.5 % (for example the MATEC 2025 5-class CNN, and SPIE PCA-SVM/CNN with a 70/30 holdout). These say **nothing** about held-out parts. [snippet-inferred].

### Inferences
- Proposed decomposition for SDP:
  1. **Symptom model** (image-only, ADR-0002-compliant): ordinal *extrusion state* (under / normal / over, plus severity) and perhaps a few appearance attributes (gloss or matte, bead roundness). Labels are derived from setpoints through physics (flow, z and temperature all map to deposited-volume and shape signatures).
  2. **Defect → cause prior table** P(cause | symptom), written from troubleshooting knowledge and CAXTON frequencies, versioned in config.
  3. **Posterior ranking** of the 8 non-none causes, each with its fix and direction, presented as a ranked array to the human. Conformal sets (already planned) wrap the symptom model.
- **Cheap test before committing (CPU, existing predictions):** on the held-out-print folds, collapse the 9 classes to symptom groups (for example {flow−, z+, temp−, speed+} vs {flow+, z−, temp+, speed−} vs none) and measure grouped accuracy against the grouped majority floor. If the grouped symptom beats its floor clearly while 9-way does not, the identifiability argument holds. The exact grouping is an inference to confirm against CAXTON's physics and the confusion matrix.

### Gaps
- No primary evidence was found that symptom-level detection generalises across prints better than parameter-level cause classification.

---

## 5. Counterfactual "what-if" explanations for process parameters

### Takeaway
DiCE-style counterfactuals are used in manufacturing to suggest setting changes, but only on **tabular** quality models, and no study validates the suggested changes on a real machine. For SDP the right place is a **forward model** (setpoints → expected bead or symptom), not the image classifier.

### Cited findings
- **Mothilal, Sharma & Tan, DiCE, FAT* 2020** — diverse, feasible counterfactuals with user constraints — [arXiv 1905.07697](https://arxiv.org/pdf/1905.07697). [snippet-inferred]. Consensus as a method.
- **MOXAI (PHM Europe 2024)** — uses DiCE to suggest machine-setting adjustments that avoid failures and quality loss — [PHM](https://papers.phmsociety.org/index.php/phme/article/download/4111/2446). The fetch failed. [snippet-inferred]. Emerging.
- **Alfeo & Cimino 2024 (BoCSoRr)** — counterfactual feature importance for production-quality regression, which they report is more reliable and cheaper than DiCE — [SciTePress](https://scitepress.org/PublishedPapers/2024/123696). [snippet-inferred]. Emerging.
- **Senoner et al., *Management Science* 2022** — SHAP on semiconductor process parameters to pick improvement actions. A precedent for "explanation → action" with SHAP rather than counterfactuals. [snippet-inferred]. Emerging.
- DiCE's robustness has been criticised, and DiPACE (Northumbria 2025) reports better plausibility on general benchmarks — [Northumbria](https://researchportal.northumbria.ac.uk/en/publications/dipace-diverse-plausible-and-actionable-counterfactual-explanatio/). [snippet-inferred].

### Inferences
- With only four bounded, ordinal parameters, DiCE is overkill. A **grid search over the forward model** (each parameter on CAXTON's range, one change at a time, consistent with the existing "one change at a time" gate rule) returns the "smallest change that brings the predicted symptom back to normal". This is exact, deterministic and testable. Fit 6.
- The forward model is learned from CAXTON with setpoints as inputs, which is legal under ADR-0002 because it is not the cause model. It also gives the *likelihood* P(symptom | cause) needed for the §4 Bayesian ranking, so §4 and §5 share one artefact.

---

## What to take for SDP

1. **Regression is not the escape hatch.** The best same-group evidence (Margadji 2024) shows flow regression degrading ~3.1× on unseen parts. Any pivot must attack *per-print appearance* directly (by reference conditioning or per-print calibration), not just change the output head.
2. **Do not reopen ADR-0002 on CAXTON.** Every logged field is either the label (commanded setpoints), a near-copy of it (`hotend`), or print identity. The sensor-fusion literature has no held-out-part cause numbers to justify the risk.
3. **Reframe "cause" as abduction.** Symptom (identifiable) → ranked causes (priors × forward-model likelihood) → fixes (forward-model what-if). This matches the objective's WHAT / WHY / ranked-fixes trio and is honest about ambiguity.
4. **Causal discovery (PC, NOTEARS) adds nothing on CAXTON**, which is interventional. Say this explicitly in the report so examiners see the choice was deliberate.
5. Cheapest decisive experiment first: grouped-symptom accuracy on existing held-out predictions (§4), then a reference-conditioned symptom model (§3).

## Pivot options ranked

| # | Option | What it changes | Evidence | ADR impact | Fit |
|---|---|---|---|---|---|
| 1 | **Symptom-first + Bayesian defect→cause ranking + forward-model fixes** | Image model predicts an ordinal extrusion symptom (under/normal/over + severity). A prior table plus forward-model likelihood ranks the 8 causes. Fixes come from a what-if grid on the forward model. | LLM-3D Print and CIPHER use the same decomposition (qualitative). Warp work uses detect-then-heuristic. Identifiability argument is an inference. | Cause model stays image-only. Output contract changes (symptom + ranked causes), so it needs a DESCEND for `types.py` and the spec. | **8** |
| 2 | **Reference-conditioned (paired / Siamese) symptom model** | Input (current crop, same-print reference crop) or a feature difference. Removes per-print appearance. | Margadji 2024 GradCAM shows the shortcut. Semi-Siamese and G-code-reference work show reference comparison is robust to setup changes (not on FFF cause). | `CauseModel.predict(crop, defect)` gains a reference crop. No setpoint input, but needs approval and a label-free reference-selection rule. | **8** |
| 3 | **Per-print few-shot calibration (Margadji recipe)** | Fine-tune the last blocks on the first k % of a held-out print, test on the rest. | [VERIFIED] MAE −8.6 / −10.1 / −12.5 with 1 / 5 / 10 calibration parts. Cross-printer 69.2 → 19.7. | Evaluation-protocol change. Needs user approval. Deployment needs a calibration print with commanded perturbations. | **6** |
| 4 | **Ordinal per-parameter regression heads** (Fast-CAXTON style) | Output head only. | [VERIFIED] still 12.3 → 38.2 MAE on unseen parts. | None beyond `types.py`. | 5 (only combined with #2 or #3) |
| 5 | **Small VLM/LLM reasoning layer** over the symptom output (local, text-only, RAG over a troubleshooting guide) | Explanation text and fix ranking. | LLM-3D Print and CIPHER: qualitative, cloud or 11B models. | None, if it consumes symptom output only. | 3 |
| 6 | **Image + telemetry fusion (reopen ADR-0002)** | Adds setpoints or `hotend`. | No held-out cause numbers anywhere. On CAXTON it is pure leakage. | Violates ADR-0002. | **1** |
| 7 | **Causal discovery (PC / NOTEARS / SCM learning)** on CAXTON | Learns a graph. | Only expert or observational-line precedents. CAXTON is interventional, so the graph is known. | None. | **2** |

Recommended path: 1 + 2 together, since the reference-conditioned model *is* the symptom model in option 1. Keep 3 as the fallback if 2 does not beat the grouped floor.

## Sources (primary first)
- Margadji, Brion & Pattinson 2024, *Addit. Manuf.* 89:104271 — https://cemag1.github.io/assets/papers/Iterative_learning%20for_efficient_additive_mass_production.pdf
- Margadji & Pattinson 2025, CIPHER, arXiv 2506.08462 — https://arxiv.org/html/2506.08462v1
- Jadhav, Pak & Barati Farimani, LLM-3D Print, arXiv 2408.14307 — https://arxiv.org/html/2408.14307v3
- Shabani & Martinez-Hernandez, IROS 2023 — https://researchportal.bath.ac.uk/en/publications/in-situ-measurement-of-extrusion-width-for-fused-filament-fabrica/
- Lin et al., arXiv 2512.24905 — https://arxiv.org/abs/2512.24905
- Waheed et al., arXiv 2602.16108 / 2602.16119 — https://arxiv.org/abs/2602.16108
- Bacha et al., iJOE 2019 — https://online-journals.org/index.php/i-joe/article/view/9375
- Marazopoulou et al., arXiv 1605.04056 — https://arxiv.org/abs/1605.04056
- Petsiuk & Pearce, arXiv 2111.02703 — https://www.arxiv.org/pdf/2111.02703
- Niu et al., Semi-Siamese, arXiv 2212.08583 — https://arxiv.org/abs/2212.08583v2
- Brion, Shen & Pattinson, warp — https://www.repository.cam.ac.uk/handle/1810/336241
- Tlegenov et al., current-based clog monitoring — https://link.springer.com/article/10.1007/s40964-019-00089-3
- Wang & Cheung 2023 KG — https://research.polyu.edu.hk/en/publications/knowledge-graph-embedding-learning-system-for-defect-diagnosis-in/
- DiCE — https://arxiv.org/pdf/1905.07697 · MOXAI — https://papers.phmsociety.org/index.php/phme/article/download/4111/2446
