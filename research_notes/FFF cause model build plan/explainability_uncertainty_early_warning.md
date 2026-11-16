# Explainability, uncertainty quantification and proactive early warning for an image-only FFF process-cause model

Scope: a nozzle-camera crop goes into a cause model that predicts flow, feed rate, z-offset and hotend temperature as low, good or high. Several causes can be active at once. The operator sees a card with a heatmap (currently EigenCAM on ResNet18 layer4), a split-conformal cause set (LAC, α=0.10), and a counterfactual setpoint proposal that passes a 4-layer safety gate. Early warning is EWMA plus hysteresis. The model may move to a multi-head (per-parameter) design.

Method note: two pages could not be fetched because their hosts are blocked in this session: pmc.ncbi.nlm.nih.gov (the Brion & Pattinson 2022 full text) and matta.ai. Anything marked "(not verified this session)" comes from background knowledge, not a page opened during this research. The report writer should treat those items as lower confidence or check them before relying on them.

---

## (a) How should the cause model's outputs be explained to an operator? (saliency, concepts, cases, human-subject evidence)

### Takeaway
Use a class-discriminative, gradient-based CAM (Grad-CAM, or EigenGradCAM / Grad-CAM++ per head) instead of plain EigenCAM. Gate any heatmap method on the Adebayo randomization sanity checks and a ROAD faithfulness score computed on our own data. Add nearest-neighbour exemplar retrieval ("looks like these labelled frames") as the case-based explanation. Evidence that heatmaps help operators is real but mixed: Senoner et al. 2024 found +7.7 pp in a factory quality-inspection field experiment, while Bansal et al. 2021 found that explanations increase acceptance of AI advice whether or not it is correct. The card should therefore always pair the explanation with confidence and uncertainty information.

### Cited Findings
**Saliency methods and sanity checks**
- Adebayo et al. (NeurIPS 2018) ran model-parameter randomization and data (label) randomization tests. Plain gradients and Grad-CAM pass. Guided Backprop and Guided Grad-CAM fail: their maps stay visually coherent even for models trained on random labels, and they behave like edge detectors. The authors call the tests necessary, not sufficient. — [Adebayo et al., NeurIPS 2018](https://papers.NeurIPS.cc/paper_files/paper/2018/file/294a8ed24b1ad22ec2e7efea049b8737-Paper.pdf); [arXiv 1810.03292](https://arxiv.org/pdf/1810.03292v2)
- In pytorch-grad-cam (`grad-cam` on PyPI), **EigenCAM takes the first principal component of the 2D activations with "no class discrimination"**. **EigenGradCAM** is the class-discriminative variant: the first principal component of Activations×Grad. — [grad-cam on PyPI](https://pypi.org/project/grad-cam/1.3.3/); [pytorch-grad-cam GitHub mirror](https://github.com/UCDvision/pytorch-grad-cam)
- pytorch-grad-cam ships ROAD faithfulness metrics in `pytorch_grad_cam.metrics.road` (`ROADMostRelevantFirst`, `ROADLeastRelevantFirst`). They can be averaged across removal percentiles and combined (MoRF/LeRF). — [grad-cam on PyPI](https://pypi.org/project/grad-cam/1.3.3/); [awesome.ecosyste.ms listing](https://awesome.ecosyste.ms/projects/github.com%2Fjacobgil%2Fpytorch-grad-cam)
- ROAD (Rong et al., ICML 2022) shows that pixel-perturbation evaluations (deletion/insertion, ROAR-style) are confounded because information leaks through the *shape* of the removed region. It uses noisy linear imputation to debias, avoids retraining (about 99% compute saved versus ROAR), and is less sensitive to removal order. — [Rong et al., PMLR 162](https://proceedings.mlr.press/v162/rong22a.html); [arXiv 2202.00449](https://arxiv.org/abs/2202.00449v2)
- Critique: Song et al. (2023) argue that ROAR and ROAD can reward attributions that carry *less* information about the model's decision function. ROAD should therefore be one signal among several, not the arbiter. — [arXiv 2304.13836](https://arxiv.org/pdf/2304.13836v1)
- ViT/DINOv2 caveat: DINOv2 (unlike DINO) produces high-norm outlier "artifact" tokens in low-information background patches, which make attention maps less interpretable. Adding register tokens (the "-reg" variants) yields smoother attention and feature maps. If the backbone moves to DINOv2, use the register variants before using any attention-rollout or attention-map explanation. — [Darcet et al., ICLR 2024 (ar5iv)](https://ar5iv.labs.arxiv.org/html/2309.16588); a 2026 cross-architecture reassessment: [arXiv 2603.25803](https://arxiv.org/abs/2603.25803)

**Domain precedent (FFF)**
- Brion & Pattinson (Nature Communications, 2022) built a multi-head deep residual attention network: one shared backbone, separate output heads per parameter, with cross-entropy computed at each head. It was trained on about 1.2 M images from 192 parts, labelled with hotend temperature, flow rate, lateral speed, Z offset (and bed temperature), using 8 Creality CR-20 Pro printers fitted with nozzle cameras. The authors produced visualisations of what the network attends to. — [DOAJ record, Nat. Commun. Aug 2022, DOI 10.1038/s41467-022-31985-y](https://doaj.org/article/b44f0b7fe6f84f93946c2b078db51cfc); [Cambridge repository](https://www.repository.cam.ac.uk/items/935de70d-18c9-4acf-b146-d18f1bd5cc83)
  - (Not verified this session, full text blocked) My recollection is that they used the attention-module masks and guided backpropagation for visualisation. Given Adebayo et al., guided backprop is a poor choice to copy.

**Concept-, prototype- and case-based explanations**
- HIVE (Kim et al., ECCV 2022) is a human evaluation on MTurk comparing GradCAM, BagNet, ProtoPNet and ProtoTree. The mean task time was about 13.6 min for ProtoPNet versus about 6.9 min for GradCAM, 6.6 min for BagNet and 10.4 min for ProtoTree, so prototype explanations roughly double the operator's cognitive time cost. — [HIVE supplementary, ECCV 2022](https://www.ecva.net/papers/eccv_2022/papers_ECCV/papers/136720277-supp.pdf)
- Sinhamahapatra et al. (VISAPP 2023) found in a user study that many ProtoPNet-learned prototypes are not judged useful or interpretable by humans. — [arXiv 2211.12173](https://arxiv.org/abs/2211.12173v1)
- Nauta et al. survey part-prototype evaluation and propose a "cheat sheet" of properties (correctness, composition, context, and others), with user studies as one evaluation route. — [arXiv 2307.14517](https://arxiv.org/pdf/2307.14517v1.pdf)

**Human-subject evidence on whether explanations improve decisions**
- Senoner, Schallmoser, Kratzwald, Feuerriegel & Netland (Scientific Reports 2024; DOI 10.1038/s41598-024-82501-9) ran preregistered field experiments. Siemens factory workers labelled 200 electronic-product images as faultless or defective in 35 minutes. Both arms got the same AI quality score, and the XAI arm also got heatmaps of likely defect locations. Task performance rose by **+7.7 pp (95% CI 3.3–12.0)** in manufacturing and **+4.7 pp (95% CI 1.1–8.3)** for radiologists. The mechanism was that workers followed correct AI predictions more often and overruled incorrect ones more often. — [arXiv 2406.08271](https://arxiv.org/pdf/2406.08271)
  - A third-party summary claims a balanced-accuracy rise from 88.6% to 96.3%. I could not verify this against the paper, so use the pp figures. — [themoonlight review](https://www.themoonlight.io/review/explainable-ai-improves-task-performance-in-human-ai-collaboration)
- Bansal et al. (CHI 2021) found that explanations **increased the chance humans accept the AI's recommendation regardless of its correctness**. Complementary team performance did appear, but explanations did not add to it compared with simply showing AI confidence. The setting was NLP tasks with matched human and AI accuracy. — [arXiv 2006.14779](https://arxiv.org/abs/2006.14779v2); [UW pdf](https://aiweb.cs.washington.edu/ai/pubs/bansal-chi21.pdf)

### Inferences
- **Replace or augment EigenCAM.** EigenCAM is not class-discriminative, so with several causes active it draws the *same* map for "flow high" and "z-offset low". That breaks the card's promise of explaining *this* cause. Use Grad-CAM, Grad-CAM++ or EigenGradCAM with `ClassifierOutputTarget(head_k, class_c)` per head; pytorch-grad-cam supports custom targets. Keep EigenCAM only as a class-agnostic "where the network looks" overlay, if at all.
- **Acceptance test for any heatmap method** (cheap, CPU-feasible on a 224 px ResNet18):
  1. Adebayo cascading randomization of layer4, then layer3. The Spearman rank correlation of the maps should drop sharply.
  2. ROAD MoRF/LeRF at percentiles {10, 20, 30, 40, 50, 70, 90} on the calibration split only, compared against a random-map baseline.
  3. Report the score per head.
- **Fine texture concern (inference).** Over-/under-extrusion and z-offset show up as bead width, gloss and texture across the whole crop, not as a localized object. Layer4 of ResNet18 at 224 px gives a 7×7 map, which is too coarse to show bead-scale texture. Consider layer3 (14×14) or input-gradient methods (IG / SmoothGrad via Captum) as a secondary view. Expect "diffuse" maps to be the correct answer for global causes, and tell operators so in the UI copy.
- **Case-based > prototypes for this project.** kNN retrieval over penultimate-layer embeddings of labelled calibration and training frames ("this looks like these 3 frames labelled flow-low at 85%") is cheap and needs no architecture change. It is also closer to how an operator reasons. ProtoPNet-style models cost accuracy, add training complexity and roughly double interpretation time (HIVE), and their prototypes are often judged uninterpretable. Restrict retrieval to *other prints* (leave-one-print-out) so the card does not show near-duplicate frames from the same print.
- **Concept bottlenecks:** the four process parameters already *are* the concepts. A multi-head model is effectively a concept-level output, so a separate CBM/TCAV layer adds little at UG scale.
- **Design implication from Bansal and Senoner:** always show calibrated confidence and set size next to the heatmap, and make "abstain / ask human" visible. Explanations alone raise blind acceptance.

### Gaps
- No human-subject study specific to FFF or additive-manufacturing operators was found. Senoner 2024 is the closest (electronics visual inspection).
- I could not open the Brion & Pattinson 2022 full text (host blocked), so their exact visualisation method, per-head accuracies and correction cadence are unverified.
- No published faithfulness benchmark (ROAD/deletion) specifically for fine-texture or industrial-surface classifiers was found. This will need our own measurement.
- Score-CAM, integrated gradients and Captum specifics (LayerGradCam, NoiseTunnel, IntegratedGradients) were not researched this session. Captum's docs at captum.ai list these, but that is not verified this session.

---

## (b) How should uncertainty be quantified with guarantees? (calibration, multi-label/multi-head conformal, shift)

### Takeaway
The four-parameter multi-head output is best handled as **four per-head 3-class split-conformal sets**, with Bonferroni α/4 if a joint guarantee is wanted. Add **class-conditional (Mondrian) calibration** for the rare low/high classes, and **group (per-print / per-material) conditional checks** for shift. If the model stays a flat multi-label output ("which causes are active"), use **Conformal Risk Control** to bound the false-negative rate (MAPIE `MultiLabelClassificationController(risk="recall", method="crc")`). Temperature scaling is good for calibrated displayed probabilities, but it **does not shrink conformal sets** and can enlarge APS sets. Fit it on a separate split from the conformal calibration set.

### Cited Findings
- Conformal Risk Control (Angelopoulos, Bates, Fisch, Lei, Schuster; ICLR 2024) extends split conformal from miscoverage to any **monotone bounded loss**, giving E[loss] ≤ α in finite samples. A worked example bounds the multi-label false-negative rate by thresholding the per-label scores (λ = inclusion threshold). — [arXiv 2208.02814](https://arxiv.org/abs/2208.02814); [ICLR 2024 proceedings](https://proceedings.iclr.cc/paper_files/paper/2024/hash/f3549ef9b5ff520a7e41ff3cc306ab2b-Abstract-Conference.html)
- Automatically Adaptive CRC (Blot, Angelopoulos et al.) extends CRC to group-conditional / input-adaptive guarantees, using the same multi-label FNR loss. — [arXiv 2406.17819](https://arxiv.org/pdf/2406.17819)
- MAPIE: `mapie.risk_control.MultiLabelClassificationController` takes `risk`. "recall" allows method "crc" (default) or "rcps", and "precision" requires "ltt" (Learn-then-Test). The default `target_level` is 0.9 with λ grid `np.arange(0, 1, 0.01)`. RCPS and LTT need a confidence level δ in (0,1). Older versions (1.0.1–1.2.1) call this `PrecisionRecallController(metric_control=...)`, so pin the version. — [MAPIE stable docs](https://mapie.readthedocs.io/en/stable/generated/mapie.risk_control.MultiLabelClassificationController.html); [MAPIE v1.0.1 PrecisionRecallController](https://mapie.readthedocs.io/en/v1.0.1/generated/mapie.risk_control.PrecisionRecallController.html)
- Class-conditional (Mondrian) conformal splits the calibration data by class and calibrates each separately, which guarantees per-class coverage. It degrades when classes have few calibration examples. **Clustered conformal** (Ding, Angelopoulos, Bates, Jordan, Tibshirani; NeurIPS 2023) pools classes with similar score distributions and beats both standard and classwise conformal on class-conditional coverage and set size in the limited-data regime. — [arXiv 2306.09335](https://arxiv.org/abs/2306.09335); [NeurIPS 2023](https://proceedings.neurips.cc/paper_files/paper/2023/hash/cb931eddd563f8d473c355518ce8601c-Abstract.html)
- Weighted conformal under covariate shift (Tibshirani, Barber, Candès, Ramdas; NeurIPS 2019) keeps coverage when the test/train covariate likelihood ratio is known, via a weighted quantile of scores. The ratio can be estimated from unlabelled test covariates. — [arXiv 1904.06019](https://arxiv.org/abs/1904.06019)
- Calibration: Guo, Pleiss, Sun & Weinberger (ICML 2017) found modern networks overconfident. **Temperature scaling** (a single parameter) was the most effective post-hoc method on vision tasks, and they measured ECE with **M = 15 equal-width bins**. Binning methods can change predicted classes. — [arXiv 1706.04599](https://arxiv.org/pdf/1706.04599)
- ECE depends on the bin count. One study varied B over 5–25 to obtain unambiguous conclusions, so report ECE at several B, or a debiased/adaptive variant. — [UDL 2021 paper 060](https://www.gatsby.ucl.ac.uk/~balaji/udl2021/accepted-papers/UDL2021-paper-060.pdf)
- Calibration before conformal: post-hoc calibration such as temperature scaling **improves calibration but increases prediction-set size** for adaptive conformal methods. Conformal-aware temperature (ConfTS/ConfTr) reportedly cut ImageNet APS set size at α=0.1 from 10.9 to 3.91. — [arXiv 2402.04344](https://arxiv.org/pdf/2402.04344)
- Dabah & Tirer: TS **improves class-conditional coverage** of adaptive CP (APS/RAPS) but **hurts set size**, and the effect of temperature is non-monotonic. — [arXiv 2402.05806](https://arxiv.org/html/2402.05806v4)

### Inferences
- **Recommended pipeline for a multi-head model** (per head k ∈ {flow, feed, z, temp}, 3 classes):
  1. Fit the temperature T_k per head on a *calibration-A* split (the val folds, grouped by print).
  2. Compute LAC scores 1 − p̂_k(y) on a disjoint *calibration-B* split.
  3. Take the quantile at level ⌈(n+1)(1−α_k)⌉/n.
  4. Use α_k = 0.10 for per-head marginal coverage. If the card claims "the true state of *all four* parameters is in these sets", use α_k = 0.10/4 = 0.025 (Bonferroni). That needs n ≳ 40/α_k ≈ 160+ calibration frames per head for a non-trivial quantile. A rule of thumb is n ≥ 1/α − 1, so about 39 for α=0.025; more reduces variance.
- **Unit of exchangeability is the print, not the frame.** Frames within a print are highly autocorrelated, so frame-level calibration overstates effective n and coverage. Calibrate on whole held-out prints. Check coverage per print (group-conditional) and per material/colour, and report the worst group. Leave-one-group-out folds in `data/splits/logo.json` fit this naturally. Never calibrate on test folds.
- **Mondrian per class:** "good" will dominate, so marginal 90% coverage can hide poor coverage on "low/high". Use classwise (Mondrian) quantiles per head when each class has ≳ 50–100 calibration frames from several prints. Otherwise use clustered conformal or pool low/high as "off-nominal".
- **LAC vs APS:** LAC gives the smallest average sets but the weakest conditional coverage. APS/RAPS give better conditional coverage with larger sets. For a safety gate, an empty set or a set containing both "low" and "high" should map to **abstain → no counterfactual proposal**.
- **Multi-label alternative:** if one sigmoid per (parameter, direction) is kept, use CRC with FNR loss at α=0.10, which means at most 10% of the true active causes are missed on average. This directly matches "possibly several at once".
- **Shift between prints:** weighted conformal needs a density-ratio estimate. At UG scale, group-conditional checks plus an online coverage monitor are more practical; see the conformal martingale in (c). Optionally add adaptive conformal inference (not researched here).
- **Tooling:** MAPIE (sklearn-style, works on precomputed softmax arrays) covers CRC/LTT. TorchCP was not checked this session. A plain NumPy implementation of LAC and Mondrian is about 20 lines and avoids a dependency, which matters given the CLAUDE.md "no new dependency" rule.

### Gaps
- No source was found on conformal prediction specifically for multi-head ordinal outputs (low/good/high is ordinal). Ordinal conformal methods with contiguous sets exist in the literature but were not researched.
- Barber et al.'s "Conformal prediction beyond exchangeability" (bounded coverage gap under drift) did not come up in the searches and is not cited.
- TorchCP API and features were not verified.
- No concrete minimum calibration-set guidance specific to autocorrelated video frames was found. The print-level advice above is inference.

---

## (c) Communicating "which parameter and which direction" (counterfactual / actionable explanations)

### Takeaway
With a per-parameter low/good/high head, the direction of correction comes straight from the model's ordinal output, so the "counterfactual" is a direct mapping (head k says "low" → raise setpoint k), not a search problem. The conformal set decides *whether* to act: act only when the set for head k is a singleton that excludes "good". The magnitude should come from a deterministic, bounded step policy behind the safety gate, not from the model.

### Cited Findings
- Brion & Pattinson's multi-head network predicted each parameter's state separately (one head per parameter) and was used for closed-loop correction of those parameters. — [DOAJ, Nat. Commun. 2022](https://doaj.org/article/b44f0b7fe6f84f93946c2b078db51cfc)
- Explanations increase acceptance regardless of correctness, and confidence display gives comparable complementarity. That argues for showing the set and confidence alongside the proposal. — [Bansal et al. CHI 2021](https://arxiv.org/abs/2006.14779v2)
- Senoner et al.'s gain came from operators overruling incorrect AI more often when they could see *where* the evidence was. A proposal should therefore come with the visual evidence for that specific head. — [arXiv 2406.08271](https://arxiv.org/pdf/2406.08271)

### Inferences
- Card wording template: "Flow likely **LOW** (set: {low}, 90% guarantee) → propose flow 100→108% (+8, max step) | z-offset: {good} | temp: {low, good} → *no action, uncertain*".
- Gate rules derived from conformal sets:
  - Propose a change for head k only if C_k ∩ {good} = ∅ and |C_k| = 1.
  - If several heads are actionable, propose **only one change at a time**, ordered by a fixed priority (for example z-offset before flow before temp). Confounded causes look alike: over-extrusion vs low z-offset both squash the bead.
  - Re-evaluate after a settling window before proposing the next change.
- The algorithmic-recourse literature (minimal-cost feature changes) is less relevant here. Setpoints are not model inputs (ADR-0002, image-only), so there is no "feature" to perturb. The mapping is a domain lookup and needs no recourse optimisation. (Inference; recourse papers were not researched in this session.)

### Gaps
- No published evidence was found on how operators respond to setpoint-change proposals specifically, or on the optimal step size per parameter. Step sizes need empirical tuning on the rig.

---

## (d) Proactive early warning before a defect is visible

### Takeaway
EWMA plus hysteresis is a reasonable baseline. Two principled upgrades fit this pipeline:
1. A **CUSUM** (or its conformal version) on per-frame evidence for each head, tuned to a target false-alarm rate per print-hour.
2. A **conformal test martingale** on the conformal p-values as a model-level "the input distribution has shifted, stop trusting the cause model" alarm. Its false-alarm guarantee comes from Ville's inequality.

BOCPD (Adams & MacKay) is a good fit when you want a posterior over "time since change" to display. Tune all thresholds on calibration prints only, using detection delay, false alarms per hour, and recall within T seconds.

### Cited Findings
- **Conformal test martingales** are a gambler's capital betting against exchangeability using conformal p-values. Vovk (Statistical Science 2021) shows they yield conformal versions of **CUSUM** and **Shiryaev–Roberts** change detectors. — [Vovk, "Testing Randomness Online", Stat. Sci. 36(4)](https://projecteuclid.org/journals/statistical-science/volume-36/issue-4/Testing-Randomness-Online/10.1214/20-STS817.pdf)
- "Retrain or not retrain" (Vovk et al. 2021) builds conformal test martingales on top of any predictor to decide when a model should be retrained after a change point. It notes that the plain Ville alarm rule (alarm when capital ≥ 1/δ) works well early but loses power later, which motivates the CUSUM / Shiryaev–Roberts variants. — [arXiv 2102.10439](https://arxiv.org/pdf/2102.10439.pdf)
- Plug-in exchangeability martingales (Fedorova, Gammerman, Nouretdinov, Vovk; ICML 2012) build martingales from conformal p-values with a learned betting function. — [ICML 2012](https://icml.cc/imls/conferences/2012/papers/808.pdf)
- Vovk's "Testing for concept shift online" proposes decomposing the martingale evidence into concept-shift and label-shift parts. — [ar5iv 2012.14246](https://ar5iv.labs.arxiv.org/html/2012.14246)
- **BOCPD** (Adams & MacKay 2007) computes the posterior over run length (time since the last change) online by message passing. At each step the run length either grows by one or resets to 0. A constant hazard λ means a prior expected run length of 1/λ. — [arXiv 0710.3742](https://arxiv.org/pdf/0710.3742); [Gundersen walkthrough](https://www.gregorygundersen.com/blog/2019/08/13/bocd/); [hazard explanation](https://metricgate.com/calculator/bocpd-online-changepoint)
- FFF early-detection precedent: 3D-EDM (2022) is a lightweight image deep-learning model to "predict and detect" likely FFF faults. — [arXiv 2203.12147](https://arxiv.org/pdf/2203.12147). Thermography can reveal defect patterns before they are visible, but that is a different sensor and not usable as model input here. — [Phillips et al., NSF PAR](https://par.nsf.gov/servlets/purl/10525325)

### Inferences
- **Signal choice.** For each head k, use the per-frame log-likelihood ratio s_t = log(p̂_k(off-nominal)/p̂_k(good)) with calibrated (temperature-scaled) probabilities. Feed it to a one-sided CUSUM: S_t = max(0, S_{t−1} + s_t − κ), alarm at S_t ≥ h. This is the SPRT-repeated form and is minimax-optimal for detection delay at a fixed false-alarm rate (Lorden; textbook result, not sourced this session). EWMA on probabilities is a smoothed version of the same idea without the optimality property.
- **Two distinct alarms on the card:**
  1. *Cause alarm*: CUSUM or EWMA per head, which raises a proposal.
  2. *Trust alarm*: a conformal test martingale on the LAC p-values of the predicted label, or on a nonconformity score of the embedding. When it crosses 1/δ (for example δ = 0.01 → capital ≥ 100), the frames no longer look like calibration data (new filament colour, lighting, camera bump). The system should then **suppress automated proposals and fall back to advisory / ask the human**. Ville's inequality gives P(false alarm ever) ≤ δ under exchangeability. Autocorrelated frames break exchangeability, so subsample (for example 1 frame per layer or per N seconds) before feeding the martingale.
- **HMM smoothing:** a 3-state (low/good/high) HMM per head, with a sticky transition matrix (self-transition about 1 − 1/expected-dwell-frames) and the calibrated softmax as emission likelihoods, gives a forward-filtered posterior. It is a principled replacement for EWMA + m-consecutive-frames, and the forward pass is a few lines of NumPy. BOCPD is the nonparametric cousin, useful to show "change began ~12 s ago".
- **"Before visible" is limited with image-only input.** The camera can only warn earlier than a *human* would notice, by accumulating weak per-frame evidence (CUSUM), not before the physics shows up in the bead. Forecasting future defects from images alone has thin evidence. 3D-EDM is the only image-only "predict" claim found, and its evidence is weak. Telemetry-based early warning (for example hotend-temperature deviation) belongs in the deterministic sensor checks per the hard rule, not the model.
- **Metrics and tuning protocol (no test leakage):**
  - Inject or label change points on **calibration prints only** (val folds in the LOGO split).
  - Metrics:
    - *Mean / median detection delay* (seconds from labelled onset to alarm).
    - *False alarms per print-hour* on runs with no defect.
    - *Recall within T s* (T = 10, 30, 60 s).
    - *Missed-change rate*.
  - Choose (θ_on, θ_off, m, cooldown) or (κ, h) by grid search to minimise delay subject to FA/h ≤ target (for example ≤ 0.5/h in advisory mode), using leave-one-print-out over the calibration folds.
  - Freeze the parameters, then report once on test folds.
  - CUSUM's average run length to false alarm (ARL₀) is roughly e^h in the simple Gaussian case (textbook, not sourced this session). Pick h from the target ARL₀ = frames_per_hour / FA_per_hour, then verify empirically.

### Gaps
- No FFF-specific paper was found that reports detection delay or false-alarms-per-hour for image-based cause monitoring. Our numbers will be first-of-kind for the project.
- I could not verify Brion & Pattinson's correction cadence (whether they aggregated N predictions before acting, and how many) because the hosts were blocked.
- CUSUM/SPRT optimality and ARL formulas are standard results but were not sourced with URLs in this session (Page 1954 / Lorden 1971 / Moustakides 1986).
- No empirical comparison of conformal martingales vs BOCPD vs CUSUM on image-classifier probability streams was found.
