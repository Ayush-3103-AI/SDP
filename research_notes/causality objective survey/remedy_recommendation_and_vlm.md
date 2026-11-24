# Remedy recommendation and natural-language diagnosis for FFF defects: prior art

Scope: how prior work goes from a detected defect to (a) a stated cause, (b) a plain-language diagnosis, and (c) a **ranked list of several fixes** that a human picks from. This note does not repeat CAXTON, domain generalisation, Grad-CAM, conformal calibration or CUSUM. Those are in `research_notes/FFF cause model build plan/`. Human-subject results already cited there (Bansal CHI 2021, Senoner Sci Rep 2024) are not repeated.

Constraints used for the fit scores: RTX 3050 4 GB; ADR-0002 (the cause model is image-only); every printer command goes through the deterministic 4-layer `gate()` (no LLM in the actuation path); 30 ms action-path budget. LLMs that write text or rank advice off the action path are allowed.

Labels: **[VERIFIED at source]** means the claim was read on the primary page (arXiv HTML/abs, publisher page, repo API). **[snippet-inferred]** means it comes from search snippets or secondary coverage only. Maturity: Consensus / Emerging / Speculative.

Context from our own results: the 9-way image cause model failed on held-out prints (top-1 0.209 vs majority 0.254). Its conformal sets average 7.1 of 9 causes. Every recommendation below is judged against that fact. **We cannot assume a reliable cause posterior.**

---

## 1. VLM/LLM-based diagnosis and correction for 3D printing

### Takeaway
There are two published FFF systems, and they take opposite routes. **LLM-3D Print** (CMU) uses zero-shot GPT-4o agents that see layer photos, query printer state and execute fixes. **CIPHER** (Cambridge, the CAXTON group) puts a trained *specialist regressor* under an LLM and uses RAG over a curated fact base. Neither produces a ranked list of alternative fixes. Both take one plan and iterate. Both need seconds per decision (15–45 s per layer and about 2.3 s), so they belong off our action path. Neither quantifies hallucination.

### Cited Findings
- **LLM-3D Print: Large Language Models To Monitor and Control 3D Printing.** Jadhav, Pak, Barati Farimani (CMU). arXiv [2408.14307](https://arxiv.org/abs/2408.14307) (v3, 27 Sep 2025). Published in *Additive Manufacturing* (2025), DOI [10.1016/j.addma.2025.105027](https://doi.org/10.1016/j.addma.2025.105027). The DOI resolves to Elsevier pii S2214860425003926. **[VERIFIED at source]** for the method and numbers, from the arXiv HTML v3. **[VERIFIED]** for the venue via DOI resolution.
  - Inputs: top and front camera images taken after each layer, with the printer paused and the head homed. The previous layer's images are included so fixed issues are not flagged again. The inputs also include a text description of the part and printer state queried on demand through Moonraker (flow, retraction, fan, Z-offset). The model sees a "curated list of modifiable G-code objects", not raw G-code.
  - Models: GPT-4o and GPT-4.1. There is no fine-tuning.
  - Architecture: 7 modules. A supervisor keeps a shared state dictionary. An image-reasoning error-detection agent finds defects. An information-gathering planner and a solution planner (with a prompt adapter) produce the plan. Three ReAct executor agents call the printer API and retry with alternative endpoints if a call fails.
  - Ranking of fixes: **none**. The planner emits one plan, and correction iterates. The authors report convergence "within approximately 5 iterations" on other printers.
  - Evaluation: confusion matrices against expert annotations and a 14-engineer user study, with no headline precision or recall given. The model flagged layer separation at layers 7 and 11 before the expert annotators did. Peak compressive load after optimisation: square part 5.06× (about 0.8 to over 4.0 kN), hexagonal 1.60×, hemispherical 1.34×, auxetic 2.46×.
  - Latency: "15 to 45 seconds" per layer.
  - Failure modes reported: a missed blob (layer 9), blobs mislabelled as stringing or oozing, minor warping misattributed, layer separation labelled inconsistently, and fine defects lost to image compression. Stringing was not removed under high-flow/low-speed/high-temp settings. Layer shift was excluded as unfixable. Full firmware documentation overflowed the 128k context and caused unintended shutdowns, which is an LLM-in-actuation-path hazard. Hallucination is not analysed.
  - Code: none linked. The project page is [printerchat](https://sites.google.com/andrew.cmu.edu/printerchat). Paper licence CC BY 4.0.
  - Maturity: **Emerging**. Fit: **3/10** as built (cloud GPT-4o, LLM actuates, seconds of latency). **6/10** as a pattern: the information-gathering step before planning and the previous-layer context are worth borrowing for off-path explanation text.

- **CIPHER: Hybrid Reasoning for Perception, Explanation, and Autonomous Action in Manufacturing.** Margadji and Pattinson (Cambridge). arXiv [2506.08462](https://arxiv.org/abs/2506.08462) (10 Jun 2025, preprint). Code [cam-cambridge/CIPHER](https://github.com/cam-cambridge/CIPHER): **MIT licence, last push 2026-03-25**, 1 star (GitHub API). **[VERIFIED at source]** from the arXiv HTML and the repo API.
  - Architecture: Llama-3.2-11B-Vision (ViT-H/14 encoder). It adds a **"process expert"**, a ResNet-152 (116 M params) that regresses **flow rate only**. Its prediction is injected into the LLM as a single token. RAG retrieves the top-5 of **3,930 facts** that an LLM generated from a 3D-printing mind map (Ada-v2 embeddings). A second RAG over Marlin G-code docs is parsed to JSON. Output is G-code, e.g. `M221 S<n>`.
  - Data: an endoscope nozzle camera with firmware flow-rate labels, from ">1 million" images (CAXTON-style). The test set has 1,000 held-out samples. The page does not say whether they are held out by print.
  - Results: flow MAE falls from 82.92 ± 71.83 (naive fine-tune) to **17.52 ± 28.89** with the process expert. Generating G-code adds 0.215 ± 0.090 error (about 1.2%). On QA correctness Elo, the authors' model with RAG scored 1197/1238/1171, below GPT-4o at 1283/1261/1305. Chain-of-thought Elo with the codebook reached about 1232–1250. The paper contains text/table inconsistencies (E.4 vs E.5 MAE, Elo values).
  - Latency: belief estimation 1.5 ± 0.8 s, correction 0.8 ± 0.4 s, about 2.3 Hz. Training used 4× A100-80GB at about 20 h per epoch. LoRA cuts memory from 199.3 GB to 94.9 GB. Inference VRAM is not reported. A 4-bit quantisation note conflicts with Table 4.
  - Multiple options: only for *geometry*, where it samples 4 shapes for the user to pick. Control gives a single rationale and command.
  - Limitations stated: joint fine-tuning caused catastrophic forgetting. Explanation reliability "warrants further scrutiny" in safety-critical settings. Hallucination reduction from RAG is not quantified. Conflict of interest: the authors are linked to Matta Labs.
  - Maturity: **Emerging**. Fit: **4/10** to run (an 11B VLM does not fit 4 GB, and it actuates). **8/10** as an architecture pattern: a small trained specialist turns the image into a *numeric belief*, and the LLM only verbalises and reasons over that belief plus retrieved facts. That matches ADR-0002 plus `gate()` exactly if the LLM's output stops at text.

- **FA3D: a fault-aware monitoring framework for 3D printing using vision-language models.** *J. Intelligent Manufacturing* (2026), [10.1007/s10845-026-02935-y](https://link.springer.com/article/10.1007/s10845-026-02935-y). **[snippet-inferred]**: the Springer page redirected to a login and could not be read. Per snippets, it uses pretrained VLMs (Gemini 2.5 Flash Image, GPT-4o, Qwen2.5-VL-32B, GLM-4.5V) in a zero-shot perceive-reason-act loop on 140 FFF images, with a **human stop/continue decision**. Numbers are unverified. Maturity: **Emerging**. Fit: **4/10**. The human gate is the relevant part, and it confirms the HITL pattern.

- **FDM-Bench.** Eslaminia et al., arXiv [2412.09819](https://arxiv.org/abs/2412.09819) (Dec 2024). Later DOI 10.1016/j.mfglet.2025.06.161 (*Manufacturing Letters*), **[snippet-inferred]**. It benchmarks GPT-4o, Claude 3.5 Sonnet and Llama-3.1-70B/405B on FDM user Q&A (MCQ plus open answers graded by an expert panel) and G-code anomaly detection. Closed models did better on G-code. Llama-405B had a slight edge on Q&A. Maturity: **Emerging**. Fit: **5/10** as a ready-made check that whatever LLM writes our explanations knows FDM basics.

- **Multimodal RAG for L-PBF anomaly classification.** Naghavi Khanghah et al., ASME IDETC 2025, arXiv [2505.13828](https://arxiv.org/abs/2505.13828). **[VERIFIED at source]** (abstract). It retrieves text and images from the literature. GPT-4o-mini beats Qwen2-VL-2B, and retrieval adds **+12% average accuracy**. It covers metal PBF, not FFF. Maturity: **Emerging**. Fit: **3/10**, but it is evidence that retrieval helps small VLMs.

- arXiv 2605.03328 (LLM-ADAM, pre-print G-code anomaly screening) and 2512.11098 (VLM-IRIS, infrared) were seen as titles or snippets only and are not relevant to remedies. **[snippet-inferred]**.

### Inferences
- No published FFF LLM system ranks *alternative* fixes. All of them commit to one plan and iterate on the physical printer. A **ranked, human-picked remedy list is an open gap**, which works in our favour as a contribution.
- The only system with a quantitative image-to-parameter number (CIPHER) gets it from a **trained specialist**, not from the VLM. The VLM adds language, not accuracy. Our failed specialist is the bottleneck, and an LLM on top would not fix it.
- Hallucination is unmeasured in every FFF paper. If we use an LLM for text, we must constrain it to verbalise only structured fields (defect, ranked causes, ranked remedies, confidence) that deterministic code produced.

### Gaps
- No held-out-by-print evaluation of LLM diagnosis exists. LLM-3D Print and FA3D use small image sets, and CIPHER's split is unclear.
- No latency or VRAM numbers exist for a ≤4 GB local VLM on FFF images.

---

## 2. Knowledge-based remedy mapping (tables, ontologies, KGs, CBR, Bayesian networks)

### Takeaway
The practical asset is the **defect → causes → solutions troubleshooting table**. A CC-BY curated version of the Simplify3D/Prusa/All3DP guides already exists as a dataset. Formal AM ontologies and knowledge graphs are mostly metal-PBF or generic and are research-grade. No FFF-specific Bayesian-network diagnoser was found. The nearest is a PBF causal BN that infers inputs backwards.

### Cited Findings
- **3D Printing Troubleshooting Guide** (dataset). Kang, Ahn, Kim (Konkuk Univ.), Mendeley Data [10.17632/88pcwt65yp.1](https://data.mendeley.com/datasets/88pcwt65yp/1), 30 Dec 2025, **CC BY 4.0**, Markdown + PDF. Each entry has Problem / Cause / Solution, curated from Simplify3D, Prusa3D Help and All3DP. **[VERIFIED at source]**. The number of entries is not stated. Maturity: **Consensus** (the content is standard practitioner knowledge). Fit: **9/10**. It is a licence-clean seed for our remedy table.
- **Keyword-RAG: Enhancing precision in question-answering for FDM troubleshooting from technical documents.** Kang and Kim, *J. Computational Design and Engineering* 13(6):68–82, 2026, [10.1093/jcde/qwag052](https://academic.oup.com/jcde/article/13/6/68/8696400). **[VERIFIED at source]**. It runs RAG over the guide above with a local **Llama 3.1 8B** generator and keywords inserted into chunks. It was tested on only 15 GPT-4o-written questions. Context recall at 10 chunks: Naive 0.658, Rerank 0.567, **Keyword 0.728**. Context precision at 4 chunks: 0.516, 0.616, **0.636**. Semantic similarity of answers: 0.767, 0.766, **0.781**. No code repo is stated. Maturity: **Emerging**. Fit: **5/10**. Even the best retrieval misses about 27% of relevant context, so a **fixed lookup keyed by defect class beats RAG** for a closed set of 9 causes.
- **Simplify3D Print Quality Troubleshooting Guide**, [simplify3d.com](https://www.simplify3d.com/resources/print-quality-troubleshooting/). It lists **27 problems** (Under-Extrusion, Over-Extrusion, Stringing or Oozing, Layer Separation, Inconsistent Extrusion, Warping and others), each with a cause/fix page. "Copyright © Simplify3D, All rights reserved." **[VERIFIED at source]** for the list and the copyright. Fit: **7/10** as a reference. Cite it and use the CC-BY dataset for anything copied.
- **Knowledge graph embedding learning system for defect diagnosis in AM (KDDAM).** Wang and Cheung, *Computers in Industry* 149:103912, 2023, [PolyU page](https://research.polyu.edu.hk/en/publications/knowledge-graph-embedding-learning-system-for-defect-diagnosis-in/). It builds an AM ontology and literature-mined triples (parameter, effect, defect, quality), then uses a relational GCN for link prediction. Reported MRR is 0.316 and 0.7, and the page does not say which metric each value belongs to. The AM process is not stated. **[VERIFIED at source]** (abstract page). Maturity: **Speculative** for us. Fit: **3/10**. A 9-cause problem does not need a learned KG.
- **DefectOnt: An Ontology for Defect Detection in Metal AM.** Carraturo and Mazzullo, arXiv [2210.04772](https://arxiv.org/abs/2210.04772). PBF-only, aligned to MASON and Onto4Additive. **[snippet-inferred]**. Fit: **2/10**.
- **Case-based reasoning for 3D-print quality.** C.J. Yang, *Int. J. Adv. Manuf. Technol.* 2022, [10.1007/s00170-022-08672-9](https://link.springer.com/article/10.1007/s00170-022-08672-9). It retrieves past cases to suggest better printing parameters. **[snippet-inferred]** (behind a paywall redirect). Maturity: **Speculative**. Fit: **4/10**. The CBR idea maps onto "show the k most similar past events from our own store and what fixed them".
- **Bayesian network causal model of AM defects.** CIRP CMS 2019 (Tampere, [trepo](https://trepo.tuni.fi/bitstream/10024/129531/1/2019_CIRP_CMS_Conference_1.pdf)). It turns a causal model into a BN for PBF, predicts defects from parameters and infers acceptable inputs backwards. **[snippet-inferred]** (the PDF was blocked by bot protection). No FFF BN diagnoser was found. Maturity: **Emerging** (BN diagnosis in general is mature). Fit: **6/10**. Backward inference from defect to cause posteriors is the right shape. A hand-specified naive-Bayes or noisy-OR layer over the troubleshooting table needs no training data.

### Inferences
- What is reliably visible in the image is often the **defect** (stringing, under-extrusion gaps, blobs), not the **parameter** that caused it. Practitioner tables encode defect → several candidate causes, each with a direction. That is a one-to-many map, and it naturally yields a *ranked list*.
- A two-stage design replaces the failed direct 9-way cause classifier. Stage 1: image to defect type (an easier, better-posed vision task). Stage 2: a KB prior P(cause | defect), optionally re-weighted by whatever weak image evidence the cause model has. The output is a ranked remedy list with an honest "the KB says these are all plausible" spread.
- Any table we ship must cite the source and record its licence (CC BY 4.0 dataset: attribution required).

### Gaps
- No public FFF defect→cause dataset has *frequencies*. The guides give order of mention, not probabilities. We would set priors by hand and calibrate them on CAXTON labels.
- Whether CAXTON's parameter perturbations map cleanly onto guide defect names (e.g. flow− → under-extrusion) has to be checked on our data.

---

## 3. Process-parameter recommendation that outputs several candidates

### Takeaway
FFF parameter-optimisation work (Bayesian optimisation, inverse networks, recommenders) is **offline or between prints**. It tunes toward a quality target over many trial prints. Its outputs are candidate *setpoint vectors*, not in-print remedies. Two ideas transfer: (1) an inverse model can return **many** parameter sets for one target, because FDM has no unique optimum; (2) **preference BO** learns from a human picking between options, which is exactly what our HITL pick provides.

### Cited Findings
- **Process Parameter Prediction for FDM Using Invertible Neural Networks.** Pelzer et al., *Polymers* 15(8):1884, 2023, [MDPI](https://mdpi.com/2073-4360/15/8/1884). It maps target properties back to process parameters. The paper argues that no single best FDM parameter set exists. **[snippet-inferred]** (the PMC page was bot-blocked). Whether it samples multiple sets is not confirmed. INNs normally sample a latent to get many solutions. Maturity: **Emerging**. Fit: **3/10**. It needs setpoint inputs, which is outside the cause model under ADR-0002.
- **Collaborative Process Parameter Recommender for Fleets of Networked Machines (3D printing).** Wang, Guo, ..., Okwudire, arXiv [2506.12252](https://arxiv.org/abs/2506.12252), 2025 preprint. Sequential matrix completion (spectral clustering + ALS) recommends speed and acceleration across 10 Ender-3 Pro printers. It claims "significantly faster convergence" with no numbers on the abstract page. **[VERIFIED at source]** (abstract). Maturity: **Emerging**. Fit: **3/10**. It is a between-print tuner.
- **Data-Driven Process Optimization of FFF with in-situ surface roughness.** Guidetti et al. (ETH), arXiv [2210.15239](https://arxiv.org/abs/2210.15239), submitted to IFAC WC 2023. Bayesian optimisation over print parameters. The abstract gives no numbers. **[VERIFIED at source]** (abstract). Related: BO-tuned force control (arXiv [2403.16470](https://arxiv.org/abs/2403.16470)), **[snippet-inferred]**. Maturity: **Consensus** that BO is the standard sample-efficient tuner. Fit: **3/10**.
- **Preferential BO from human judgements of printed-part images.** Deneault et al., 2025 (RSC *Digital Discovery*, [d4dd00320a](https://pubs.rsc.org/en/content/articlepdf/2025/dd/d4dd00320a)). It covers extrusion printing in general. **[snippet-inferred]**. Maturity: **Emerging**. Fit: **5/10**. The idea of treating "operator picked option B over A" as a preference label carries over to learning remedy priors.

### Inferences
- These systems answer "which setpoints for the next print". Our question is "which correction now". Their outputs can at most seed the *magnitude* of a remedy step. The step itself stays fixed and bounded by `gate()`.
- The HITL choice log (which remedy the operator picked, and whether the defect cleared) is training data for remedy priors. A per-(defect, remedy) Beta-Bernoulli success count is the minimal version. This is an inference with no FFF precedent: **Speculative**.

### Gaps
- No FFF work evaluates a ranked remedy list by "was the right fix in the top-k?". We would define that metric ourselves (remedy hit@k on CAXTON's known perturbation labels).

---

## 4. Commercial and open systems

### Takeaway
Every deployed monitor **detects gross failures and pauses or notifies**. None diagnoses a process-parameter cause or recommends a fix. They detect spaghetti, detachment, blobs, layer shift and clumping. They use a per-frame CNN score with a user-set threshold, and the vendors openly admit false positives. Parameter-level, ranked remedy advice is not offered by any of them.

### Cited Findings
- **Obico** (formerly The Spaghetti Detective). [How Obico AI failure detection works](https://www.obico.io/blog/how-obico-ai-failure-detection-works/). It detects spaghetti, print detachment, layer shifts and nozzle blobs. It explicitly does **not** detect clogs, under-extrusion, stringing, minor quality issues or early failures. A CNN scores each frame (every 30–60 s) against a user sensitivity threshold. The actions are a phone notification and an optional pause (OctoPrint, Moonraker, Bambu). "We don't publish a single accuracy number." A separate First Layer AI ("Celestrius") checks first-layer under-extrusion and adhesion. It gives **no cause or fix recommendation**, only a general troubleshooting guide. **[VERIFIED at source]**. Server [TheSpaghettiDetective/obico-server](https://github.com/TheSpaghettiDetective/obico-server): **AGPL-3.0, last push 2026-11-19**, 1.9k stars (GitHub API). The vendor's next-gen model claims 56% fewer false alerts, **[snippet-inferred]**. Maturity: **Consensus**. Fit: **4/10**. Borrow the UX (sensitivity slider, snapshot plus alert), not the model.
- **Bambu Lab.** Per snippets, the H2-series nozzle camera detects nozzle clumping, "air printing" and spaghetti. Clumping is also probed via the extrusion-force or eddy sensor at layers 4, 11 and 20. The X1 lidar scans the first layer and calibrates flow. Users report false clumping alerts (one forum thread describes resuming the same error 7 times). [Bambu wiki: intelligent detection](https://wiki.bambulab.com/en/h2/manual/intelligent-detection) (returned HTTP 402 to the fetcher), **[snippet-inferred]**. Fit: **2/10** (closed).
- **PrintPal PrintWatch.** OctoPrint plugin [printpal-io/OctoPrint-PrintWatch](https://github.com/printpal-io/OctoPrint-PrintWatch): **AGPL-3.0, last push 2025-09-26**. Cloud inference with pause, stop and heater-off actions and a default threshold of about 60% (All3DP). **[snippet-inferred]** for behaviour, **[VERIFIED]** for licence and date. PrintPal's site offers *calculators* (E-steps, flow rate) that fix under- or over-extrusion offline, not in-print diagnosis. **[VERIFIED at source]**. Fit: **3/10**.
- **PrintGuard** (open, local). [oliverbravery/PrintGuard](https://github.com/oliverbravery/PrintGuard): **GPL-2.0, last push 2026-11-16**, 380 stars. It runs locally in Docker or as a desktop app and pauses with a snapshot alert. **[VERIFIED at source]** (repo API description). A Home Assistant fork publishes a 1–10 quality score over MQTT. Fit: **4/10**. It is a local baseline for gross-failure detection if we ever need one. Its GPL licence means do not vendor its code.
- **Prusa (Buddy3D / Connect).** No official AI failure detection was found. A forum thread asks why there is no spaghetti detection. **[snippet-inferred]**. **SimplyPrint** (third party) detects spaghetti, warping and blobbing and can pause or cancel. **[snippet-inferred]**.

### Inferences
- The market splits into "detect and stop" (all vendors) and "how to fix" (static guides). **Joining them with a ranked, explained fix list that a human approves is the gap** our project can claim. This is a positioning statement, and it is safe because none of the inspected products claims it.
- The vendors' honesty about false positives and their use of a user-tunable threshold support our design: abstain or defer is a first-class output, not a failure.

### Gaps
- No vendor publishes precision or recall, so there is no external baseline number to compare against.

---

## 5. HITL evidence: ranked list or set vs a single recommendation

### Takeaway
Showing a human a **small set** to choose from beats a single top-1 *when the set is small and the case is hard or out-of-distribution*. Large sets, or easy in-distribution cases, can *lower* human accuracy compared with top-k. Our current average of 7.1 of 9 is far into the "too large to help" regime. Pairing sets with **defer/abstain** (D-CP) makes the remaining sets smaller and more useful. Fixed top-k is a weaker baseline than conformal sets at equal coverage.

### Cited Findings
- **Improving Expert Predictions with Conformal Prediction.** Straitouri, Wang, Okati, Gomez-Rodriguez, ICML 2023, [PMLR v202](https://proceedings.mlr.press/v202/straitouri23a.html). The expert must choose *from* the conformal set. The authors prove a range of coverage levels under which the expert does better, give a method to find a near-optimal α, and show the result is robust to classifier accuracy (simulation with real expert predictions). Code is in Networks-Learning. **[snippet-inferred]** (abstract via search, consistent with PMLR listing). Maturity: **Emerging**. Fit: **8/10**. "Operator picks from the set" is exactly our HITL pick.
- **Conformal Prediction Sets Improve Human Decision Making.** Cresswell, Sui, Kumar, Vouitsis, ICML 2024, [PMLR v235](https://proceedings.mlr.press/v235/cresswell24a.html), arXiv [2401.13744](https://arxiv.org/abs/2401.13744). A pre-registered RCT. Conformal sets improved human accuracy over **fixed-size top-k sets with the same coverage** (p < 0.05 in three tasks). Sets did not always speed up decisions. **[snippet-inferred]** (abstract via search). Maturity: **Emerging**. Fit: **8/10**.
- **Evaluating the Utility of Conformal Prediction Sets for AI-Advised Image Labeling.** Zhang, Chatzimparmpas, Kamali, Hullman, CHI 2024 (Best Paper HM), arXiv [2401.08876](https://arxiv.org/abs/2401.08876). n = 600 compared sets, top-1 and top-k under five covariate shifts. Sets helped on **OOD images, especially when small**. In-distribution they gave **lower** accuracy than top-k, and on easy images they were on par with or worse than top-1/top-k. **[snippet-inferred]** (abstract via search). Maturity: **Emerging**. Fit: **9/10**. Our held-out prints are the OOD case, but 7.1/9 is not "small".
- **On the Utility of Prediction Sets in Human-AI Teams.** Babbar, Bhatt, Weller, IJCAI 2022, [proceedings](https://www.ijcai.org/proceedings/2022/341). RAPS sets beat top-1 for team performance (n = 120, CIFAR-100). **D-CP** (defer some inputs to the human entirely, give sets on the rest) was rated more useful and provably shrinks the sets on the non-deferred inputs. **[snippet-inferred]**. Maturity: **Emerging**. Fit: **9/10**. It is the direct recipe for "abstain or defer + short ranked list".
- **Towards Human-AI Complementarity with Prediction Sets.** De Toni, Okati, Thejaswi, Straitouri, Gomez-Rodriguez, NeurIPS 2024, [proceedings](https://proceedings.neurips.cc/paper_files/paper/2024/hash/37d4d4413b7c7558cc27a6d3d42ea998-Abstract.html). Conformal sets are in general suboptimal for human accuracy, and the optimal set is NP-hard. A greedy algorithm provably matches or beats CP for a broad class of expert models. Code: Networks-Learning/towards-human-ai-complementarity-predictions-sets. **[snippet-inferred]**. Maturity: **Speculative** for us (it needs an expert-confusion model we don't have). Fit: **4/10**.
- **Consistent Estimators for Learning to Defer to an Expert.** Mozannar and Sontag, ICML 2020, [PMLR v119](https://proceedings.mlr.press/v119/mozannar20b.html). A consistent convex surrogate for predict-or-defer, learned from expert decisions. **[snippet-inferred]**. Maturity: **Consensus** as the base L2D method. Fit: **5/10**. We lack expert-decision labels until the HITL log exists. Before that, a confidence or set-size threshold for deferral is the practical stand-in.

### Inferences
- **Present a capped, ranked list (about 3) plus an explicit "not sure, inspect manually" option.** Do not show a 7-item set. The evidence says large sets don't help and can hurt. Deferral should fire when the set is too large, which today is most of the time and is an honest outcome.
- Rank *remedies*, not causes. Several causes share a remedy family (e.g. under-extrusion from flow− or temp−), so collapsing a large cause set onto a few remedy groups shrinks what the human sees without lying about the coverage.
- Measure the HITL claim the way these papers do: operator accuracy with list vs top-1 vs no AI, on held-out prints. That is a small within-team study, not a claim we can borrow.

### Gaps
- All of these studies use image labelling, not process control. No FFF HITL study exists. Transfer is an assumption.

---

## What to take for SDP

1. **Split "what" from "why" (two-stage diagnosis).** Image → *defect type* (stringing, under-extrusion gaps, blob, over-extrusion …) is a better-posed vision task than image → 9 parameter causes. Then a **deterministic defect → {cause, direction, remedy} table** gives the candidate causes. Seed the table from the CC-BY Kang/Ahn/Kim troubleshooting dataset and cite Simplify3D/Prusa. Source: [Mendeley 88pcwt65yp](https://data.mendeley.com/datasets/88pcwt65yp/1). The cause model stays image-only (ADR-0002). The table is a fixed lookup, not a model input. *Needs a DESCEND only if it changes `xqi/types.py` or the 06–09 specs. Propose it to the user and do not patch it in.*
2. **Rank remedies with a transparent score**: score(remedy) = Σ over causes of P_KB(cause | defect) × w_img(cause) × [remedy fixes cause]. Here w_img is the (weak) image-model posterior, flattened toward uniform when its conformal set is large. This is a hand-built naive-Bayes/noisy-OR layer in the BN spirit of the CIRP CMS 2019 paper. It needs no new dependency and runs in microseconds. Keep it off `gate()`. Each remedy is still a gate-checked action when chosen.
3. **Show a capped list of about 3 plus "defer/inspect"**, following D-CP (Babbar IJCAI 2022) and Zhang CHI 2024. Our 7.1/9 sets are too large to help a human. Collapse causes into remedy groups and defer when the group set is still large. Report remedy hit@1 and hit@3 on held-out prints against the majority floor.
4. **The LLM, if any, verbalises structured output only**, following the CIPHER pattern ([arXiv 2506.08462](https://arxiv.org/abs/2506.08462)). Deterministic code produces {defect, ranked remedies, confidence, Grad-CAM region}. An LLM (or a plain f-string template first; the ponytail default) turns that into 2–3 sentences off the action path. On 4 GB, an 11B VLM won't fit. A ≤3–4B 4-bit text model or the CPU is the ceiling (an inference, not measured). Never let it emit G-code. LLM-3D Print's context-overflow shutdown is the cautionary case ([arXiv 2408.14307](https://arxiv.org/abs/2408.14307)).
5. **Log every pick and its outcome** (remedy chosen, defect cleared within N layers or not) and update per-(defect, remedy) Beta counts. This is preference learning in the spirit of preferential BO (Deneault 2025). It is speculative, and it is the only route by which the ranking improves without retraining the failed image model.
6. **Positioning:** Obico, Bambu, PrintPal and PrintGuard all detect and pause, and none recommends parameter fixes. LLM-3D Print and CIPHER fix but commit to one plan with no ranking and no human pick. "Ranked, explained, gate-checked, human-picked remedies" is unclaimed in what we inspected.

Not worth doing: learned AM knowledge graphs (KDDAM), RAG over the guide (a fixed lookup beats 0.73 context recall for a closed 9-cause set), between-print BO or INN tuners (wrong question, and they need setpoint inputs), any cloud VLM in the loop.
