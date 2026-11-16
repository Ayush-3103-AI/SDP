# Modelling methods to improve cross-print generalisation of an image-only FFF deviation classifier

Scope: a CAXTON-style nozzle-crop classifier (ResNet18 at 224 px; 9-way single-cause softmax trained on the 6.6% of images where exactly one parameter is off; balanced accuracy 0.43 on seen prints and 0.21 on unseen prints). The targets are 4–6 GB VRAM laptops and a UG team working over days to weeks. Input stays image-only (ADR-0002).

Method note: in this session, WebFetch could not reach arxiv.org, nature.com or pmc.ncbi.nlm.nih.gov because DNS was blocked. Every finding below comes from search-result abstracts and snippets, not from full-text reading. Treat specific numbers as abstract-level claims and check them against the PDFs before quoting them in a report. The hosts arxiv.org, www.nature.com and pmc.ncbi.nlm.nih.gov have to be allowed in the session network settings before anyone can verify full text.

## Prioritised shortlist (summary of the inferences below)

| # | Technique | Expected benefit (evidence strength) | Cost on a 4 GB GPU | Notes |
|---|---|---|---|---|
| 1 | Fix the evaluation protocol (grouped CV, model selection on held-out prints, bootstrap CIs over prints) | Prerequisite: without it no gain can be trusted (strong: DomainBed) | ~0 | Selection protocol alone moves DomainBed averages by several points |
| 2 | Multi-head 4×3 formulation trained on all images (CAXTON's own design) | Likely large: about 15× more training data and a matched reference design (moderate: CAXTON paper) | ~0 | Sum of 4 CE losses; derive cause probabilities from the heads |
| 3 | Temporal aggregation of per-frame probabilities (mean of log-probs over a window inside one setpoint segment) | Likely sizeable at almost no cost (inference, no direct FFF ablation found) | ~0 | Do this before any video network |
| 4 | Weight averaging (SWA/EMA, SWAD-style) plus a small ensemble | +3–4 pts over ERM on DomainBed (moderate) | ~0 training memory; ensembles cost N× inference | Also stabilises model selection |
| 5 | Strong pretrained backbone with LP-FT (linear probe, then fine-tune), e.g. DINOv2 ViT-S/14 (21M) or ConvNeXt-T | LP-FT about +10% OOD vs plain FT across 10 shift benchmarks (moderate) | ViT-S fits 4 GB with AMP and small batch or grad checkpointing | Try a frozen DINOv2 probe first as a cheap baseline |
| 6 | Domain-specific augmentation (hue/colour jitter, grayscale, blur, scale crops) plus MixStyle | Moderate, cheap; "ERM + augmentation" is competitive in WILDS-style studies | ~0 | Do not augment away the signal (see the augmentation section) |
| 7 | Label-lag handling (drop the first N seconds after each setpoint change) plus logit adjustment for imbalance | Cleaner labels; logit adjustment is Fisher-consistent for balanced error (strong theory) | ~0 | N comes from a lag sweep on validation prints only |
| 8 | Per-print reference normalisation and test-time BN (AdaBN) | Uncertain; can help covariate shift but fails under label-shifted, non-iid streams | low | Only with care: print streams are temporally correlated |
| 9 | Explicit DG losses (GroupDRO, IRM, CORAL, DANN with print ID as domain) | Usually ≤1 pt over tuned ERM (strong: DomainBed, WILDS) | low–moderate | Low priority. CORAL is the most consistent of these. |
| 10 | Video networks (TSM, 3D-CNN, video transformers) | Unproven for this task; TSM gives temporal modelling at 2D cost | TSM ~2D cost; 3D/video transformers likely too heavy | Only after #3 plateaus |

---

## Q1. Multi-head / multi-task per-parameter formulation vs single-label

### Takeaway
The reference system for this exact data, CAXTON (Brion & Pattinson 2022), uses one multi-head network with a cross-entropy loss per parameter head. It is trained on all images labelled by deviation from optimal settings, and it reports generalisation to unseen parts, materials and printers. That makes 4 heads × 3 classes, trained on all ~1M images, the most evidence-backed next step. The current setup trains on only 6.6% of the data.

### Cited Findings
- CAXTON uses inexpensive webcams and a single multi-head CNN for error detection, correction and parameter discovery. Each image is labelled by how far its printing settings sit from optimal values, with no human annotation — [Brion & Pattinson 2022, Nat. Commun. (IDEAS abstract)](https://ideas.repec.org/a/nat/natcom/v13y2022i1d10.1038_s41467-022-31985-y.html); [PMC full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC9378646)
- The network is trained with a cross-entropy loss at each head, in three transfer-learning stages — [Bohrium paper summary](https://www.bohrium.com/paper-details/generalisable-3d-printing-error-detection-and-correction-via-multi-head-neural-networks/817338338762555392-10026)
- Dataset size is reported inconsistently: about 1.2M images from 192 parts in the abstract, and about 950k in press coverage — [IDEAS](https://ideas.repec.org/a/nat/natcom/v13y2022i1d10.1038_s41467-022-31985-y.html); [AIhub/Cambridge press](https://aihub.org/2022/09/16/algorithm-learns-to-correct-3d-printing-errors-for-different-parts-materials-and-systems/)
- A model trained on one material and one printer detected and corrected errors on other materials (including ketchup and mayonnaise) and on a different printer — [Cambridge news release](https://cam.ac.uk/research/news/algorithm-learns-to-correct-3d-printing-errors-for-different-parts-materials-and-systems)
- A companion CAXTON paper trained a RegNet regression model on more than 250,000 images, each labelled with the active extrusion rate, to predict flow correction. It reports rapid correction on new parts and learning the optimal flow for unseen materials such as foaming PLA — [Brion & Pattinson 2022, Adv. Intell. Syst. (Cambridge repo)](https://www.repository.cam.ac.uk/handle/1810/339806); [DOAJ](https://doaj.org/article/9bd52b3579b64e408bd7a29de2e5454c)

### Inferences
- Implementation (PyTorch): use a shared backbone, then `nn.ModuleList([nn.Linear(d, 3) for _ in range(4)])`, with loss = Σ_k w_k · CE(logits_k, y_k) and w_k = 1 to start. Optionally add per-head class weights or logit adjustment (Q7). Uncertainty-weighting or GradNorm are possible later; with only 4 similar 3-way heads, equal weights are the sensible default. No source was found comparing balancing schemes on this data.
- Combining heads into a single-cause probability for the existing 9-way + "good" interface: assume conditional independence across heads given the image. P(only parameter k deviates in direction d) ∝ p_k(d) · Π_{j≠k} p_j(good), and P(all good) = Π_j p_j(good). Renormalise over the 9 single-cause states plus "all good" (and "multiple" if wanted). The product is cheap and transparent. Its calibration should be checked on held-out prints (ECE or reliability plot), with temperature scaling per head fitted on the calibration split.
- Multi-head training uses all ~1M images, with multi-deviation frames supervising every head. A 15× increase in training data is the main expected gain, and it directly targets the overfitting to print appearance behind the 0.43 vs 0.21 gap. This is an inference: no ablation of single-label vs multi-head on CAXTON was retrieved.
- Report per-parameter balanced accuracy for each head (the CAXTON comparison) and also the derived 9-way balanced accuracy (comparable to the current baseline).

### Gaps
- The CAXTON paper's per-head accuracies, crop size, augmentation list and train/val/test split could not be read because nature.com and PMC were blocked. The full text should be checked for these and for whether images just after a parameter change were removed.
- No published ablation of single-label vs multi-head training on CAXTON was found.

## Q2. Temporal models and temporal aggregation

### Takeaway
No controlled single-frame vs multi-frame ablation on FFF camera data was found. The cheapest step with low risk is averaging per-frame log-probabilities over a short window inside one setpoint segment. If a learned temporal model is wanted, TSM adds temporal modelling to a 2D ResNet at zero extra FLOPs and parameters, so it fits 4 GB. 3D-CNNs and video transformers are hard to justify on this hardware.

### Cited Findings
- TSM shifts some channels across neighbouring frames and adds temporal modelling to 2D CNNs at zero extra FLOPs and parameters. Its authors claim 3D-CNN-level accuracy at 2D cost — [Lin et al., TSM (arXiv 1811.08383)](https://arxiv.org/abs/1811.08383v1); [MIT-IBM blog](https://mitibmwatsonailab.mit.edu/research/blog/tsm-temporal-shift-module-for-efficient-video-understanding/)
- TSM on Something-Something V1 beats I3D and ECO with 6× and 2.7× fewer FLOPs. It reports 1.8% higher accuracy than I3D with 8× lower latency and 12× higher throughput on a P100, and 13 ms online latency on a Jetson Nano (author benchmarks) — [arXiv 1811.08383](https://arxiv.org/pdf/1811.08383.pdf)
- Caveat: the shift is zero FLOPs but adds data movement whose latency is not negligible — [TSM extension (arXiv 2109.13227)](https://arxiv.org/pdf/2109.13227)
- For FFF extrusion defects, CNN+LSTM reached 98.2% and 98.4% accuracy (front and side camera), and CNN+self-attention reached 99.3% with both cameras. The authors credit the temporal layers with catching gradual extrusion drift. This is a different dataset, with no single-frame ablation retrieved — [Georgia Southern study](https://scholars.georgiasouthern.edu/en/publications/deep-learning-enabled-infrared-monitoring-for-in-process-anomaly-/)
- A 2025 review compares FDM visual monitoring methods by accuracy, response speed and integration effort — [Herald of KhNU review](https://heraldts.khmnu.edu.ua/index.php/heraldts/en/article/view/1885)

### Inferences
- With settings changing every ~12 s, a causal window of 1–3 s within one segment can be averaged with no label conflict. In deployment, use an EMA or sliding mean of log-probs per head. Because the model is image-only, this does not break ADR-0002. Per-frame errors driven by print appearance are correlated within a print, so averaging removes frame noise but not print-level bias. The gain on unseen prints may therefore be smaller than on seen prints. Measure it rather than assume it.
- Frame stacking (k frames as 3k input channels) breaks ImageNet first-layer weights. TSM keeps them and fits the ResNet18 budget: at 8 frames × 224 px, activation memory is roughly 8× a single-image batch, so cut the batch size accordingly.
- 3D-CNNs (R(2+1)D, X3D) and video transformers (VideoMAE, TimeSformer) carry heavy activation memory. On 4 GB they would need tiny clips, small batches and gradient checkpointing. They are not recommended within the UG timeframe, and no FFF evidence supports them.
- Latency: the loop's decision rate is seconds, so window aggregation adds latency equal to the window length. That is acceptable if the window is about 1–2 s.

### Gaps
- No study was found that isolates the benefit of temporal input over single frames on CAXTON or similar nozzle-camera data.
- No measured VRAM figures for TSM-ResNet18 or VideoMAE-S on 4 GB GPUs were found. Measure them with `torch.cuda.max_memory_allocated()`.

## Q3. Reference-frame / per-print normalisation and test-time adaptation

### Takeaway
Re-estimating BN statistics on target data (AdaBN / prediction-time BN) improves robustness to covariate shift in several studies. However, test-time adaptation (TENT and BN updating) is fragile under small batches, mixed shifts and non-iid, label-shifted streams, which describes a print stream with 12 s blocks of one setpoint. Per-print reference methods (difference to early "good" frames, Siamese comparison) are well motivated but have no direct evidence here. They should be tried as a cheap ablation with care about the reference assumption.

### Cited Findings
- Re-estimating BN statistics on corrupted test images improved robustness across 25 vision models (ImageNet-C) — [Schneider et al., NeurIPS 2020](https://papers.nips.cc/paper_files/paper/2020/file/85690f81aadc1749175c187784afc9ee-Paper.pdf); [arXiv 2006.16971](https://arxiv.org/pdf/2006.16971v2)
- AdaBN recomputes BN statistics on the target domain at test time. Prediction-time BN does not help as much for some other types of shift — [Nado et al. 2020 (arXiv 2006.10963)](https://arxiv.org/pdf/2006.10963); [NSF PAR copy](https://par.nsf.gov/servlets/purl/10338574)
- Test-time normalisation can degrade discriminative structure when target batch statistics mismatch the source parameters — [arXiv 2110.04065](https://arxiv.org/pdf/2110.04065.pdf)
- SAR identifies BN as a major cause of TTA instability. Mixed shifts, small batches and online imbalanced label shift hurt TTA, and TENT-style entropy minimisation can collapse to predicting one class — [Niu et al., "Towards Stable Test-Time Adaptation" (SAR, ICLR 2023)](https://tanmingkui.github.io/files/publications/Towards_Stable.pdf)
- The TTAB benchmark ("On Pitfalls of Test-time Adaptation", ICML 2023) documents TTA failures under label shift and non-iid streams — [TTAB repo](https://github.com/LINs-lab/ttab)

### Inferences
- Print streams are strongly non-iid. A 12 s block has one fixed label, and some prints are mostly "good". Per-batch BN re-estimation or TENT would partly normalise away the deviation signal (for example, a whole block of under-extrusion becomes the "mean"). Prefer a fixed per-print reference: estimate BN stats or a feature mean and std from the print's first N seconds, where settings are good, then freeze them. This requires an operational guarantee that the start of each print runs at good settings. Check whether that holds in CAXTON. If it does not, the reference is contaminated, and the method leaks the label prior into the test fold.
- Per-print feature standardisation (subtract the print reference mean embedding, then probe) and difference images are both cheap (≤1 day). Treat them as ablations, not defaults.
- Siamese or contrastive "is this frame different from my reference" heads are attractive for interpretability, but no supporting evidence was found. Mark them as speculative.
- If TTA is tried, use SAR-style reliable-sample filtering, or update only norm statistics with momentum. Report results with and without TTA, and never tune TTA hyperparameters on test folds.

### Gaps
- No AM or FFF paper using per-print reference normalisation or TTA was found.
- The specific accuracy gains of TENT and SAR on standard benchmarks were not retrieved because arXiv full text was blocked.

## Q4. Domain-generalisation methods vs ERM

### Takeaway
On DomainBed and WILDS, well-tuned ERM is very hard to beat. No DomainBed algorithm beats ERM by more than ~1 point under equal conditions, and in WILDS Camelyon17 ERM beat IRM, CORAL and GroupDRO. The techniques that do reliably help are weight averaging and ensembling (SWAD, EoA: +3 to 4 pts over ERM) and stronger pretraining or augmentation.

### Cited Findings
- No DomainBed algorithm outperforms carefully tuned ERM by more than 1 point under the same conditions. ERM averages 85.5 on PACS with ResNet-50 — [Gulrajani & Lopez-Paz, ICLR 2021 (arXiv 2007.01434)](https://arxiv.org/pdf/2007.01434); [ICLR page](https://iclr.cc/virtual/2021/poster/2998)
- Model selection matters: one review reports ERM averages of 68.9% with oracle test-domain selection, 67.0% with training-domain validation and 63.8% with leave-one-domain-out. These come from a third-party review and need verifying — [Liner review](https://liner.com/review/in-search-of-lost-domain-generalization)
- WILDS Camelyon17 test accuracy: ERM 70.3 ± 6.4, IRM 64.2 ± 8.1, CORAL 59.5 ± 7.7, GroupDRO 68.4 ± 7.3 (as tabulated in LISA). The ERM ID validation figure is 84.9 — [LISA (arXiv 2201.00299)](https://arxiv.org/pdf/2201.00299); [WILDS leaderboard](https://wilds.stanford.edu/leaderboard)
- An empirical study finds that with proper pretrained models, GroupDRO and CORAL can reach SOTA on some datasets, while ERM with data augmentation is also very competitive — [arXiv 2205.12753](https://ar5iv.labs.arxiv.org/html/2205.12753)
- Under its own protocol, Fishr reports 70.8% vs 69.2% for CORAL (the second best). Independent reproductions show smaller gaps — [Fishr (arXiv 2109.02934)](https://arxiv.org/pdf/2109.02934)
- ERM++ reports a gain of more than 5% over prior ERM baselines on 5 DG datasets with ResNet-50 (self-reported) — [ERM++ (arXiv 2211.14594)](https://arxiv.org/pdf/2211.14594v4.pdf)
- SWAD (dense stochastic weight averaging to reach flat minima) reports SOTA on 5 DomainBed datasets, +1.6 pts over prior SOTA and about +3.6 over ERM (secondary summary) — [SWAD, NeurIPS 2021](https://proceedings.neurips.cc/paper/2021/hash/bcb41ccdc4363c6848a1d760f26c28a0-Abstract.html); [alphaXiv overview](https://alphaxiv.org/overview/2102.08604v4)
- EoA (ensemble of moving-average models) reaches 68.0% on DomainBed with ResNet-50, about 4 pts above ERM, and 76.6% with RegNetY-16GF, about 6 pts above ERM. It also makes model selection more reliable — [Arpit et al., NeurIPS 2022](https://proceedings.neurips.cc/paper_files/paper/2022/hash/372cb7805eaccb2b7eed641271a30eec-Abstract.html); [DeepAI abstract](https://deepai.org/publication/ensemble-of-averages-improving-model-selection-and-boosting-performance-in-domain-generalization)
- MixStyle mixes instance-level feature statistics (style) across training samples in the shallow CNN layers to synthesise new domains. A ResNet-18 PACS average of 83.7 is listed as unverified — [Zhou et al., ICLR 2021 (arXiv 2104.02008)](https://arxiv.org/abs/2104.02008v1); [leaderboard entry](https://sotaverified.org/papers/domain-generalization-with-mixstyle-1)

### Inferences
- First priority: weight averaging. `torch.optim.swa_utils.AveragedModel`, with averaging started early in training, adds almost no VRAM (one extra copy of the ResNet18 weights, about 45 MB). An ensemble of 3–5 averaged seeds is the EoA recipe; it costs N× inference but is still well within real-time budgets for ResNet18.
- MixStyle is a drop-in module of about 20 lines after layer1 and layer2 of the ResNet. With 192 prints, the "domains" are the prints, and mixing across samples in a batch from different prints is cheap. This is the DG method most aligned with the failure (per-print appearance, i.e. style), but its gains over a well-tuned ERM baseline are uncertain.
- GroupDRO, IRM, CORAL and DANN with print ID as domain are low priority. The benchmark evidence says expect ≤1 pt, and WILDS shows they can hurt. If one is tried, CORAL is the most consistent in reproductions. DANN with 192 domains needs a 192-way discriminator and a gradient reversal layer, which is cheap in memory but fiddly to tune.

### Gaps
- No AM or FFF paper benchmarking DG methods with print or part as the domain was found.
- The original MixStyle ResNet-18 baseline vs MixStyle numbers were not verified.

## Q5. Self-supervised / foundation backbones under 4–6 GB VRAM

### Takeaway
The strongest evidence for OOD gains from backbone choice is LP-FT: fit a linear head on frozen features first, then fine-tune. Across 10 shift benchmarks, full fine-tuning gave about +2% ID but about −7% OOD vs linear probing, and LP-FT gave about +10% OOD over full fine-tuning. DINOv2 ViT-S/14 (~21M parameters) is small enough for 4 GB with AMP, and its frozen features are reported to transfer well, including in out-of-domain imaging (medical, geology). No AM-specific DINOv2 evidence was found.

### Cited Findings
- Across 10 distribution-shift benchmarks, fine-tuning averaged about 2% higher ID accuracy but about 7% lower OOD accuracy than linear probing. The gap appears when pretrained features are good and the shift is large — [Kumar et al., ICLR 2022 (arXiv 2202.10054)](https://arxiv.org/abs/2202.10054)
- LP-FT (linear probe, then full fine-tune) gave about +1% ID and +10% OOD vs fine-tuning, and changes features 10–100× less — [ICLR 2022 oral](https://iclr.cc/virtual/2022/oral/5946); [NSF PAR PDF](https://par.nsf.gov//servlets/purl/10337813)
- The DINOv2 paper evaluates frozen features with linear heads on domain-generalisation benchmarks, ImageNet-A/C/R/Sketch (Table 6) — [Oquab et al. (arXiv 2304.07193)](https://arxiv.org/pdf/2304.07193)
- DINOv2 ViT-S/14 has about 21M parameters, patch 14 and embedding dimension 384 — [DINOv2 model card](https://github.imc.re/DavidFM43/dinov2-knn/blob/main/MODEL_CARD.md)
- DINOv2 performs well out of the box without encoder fine-tuning on medical imaging — [arXiv 2312.02366](https://arxiv.org/pdf/2312.02366v3)
- DINOv2 is effective for geological image classification and segmentation, with LoRA plus 4-bit quantisation for larger variants — [arXiv 2407.18100](https://arxiv.org/pdf/2407.18100)
- Fine-tuning ViT-S/14 in histopathology used batch 256, and batch 128 gave similar results (A100) — [arXiv 2401.04720](https://arxiv.org/pdf/2401.04720)
- LoRA on a DINOv2 backbone significantly reduces training time and GPU memory, especially for larger models — [arXiv 2403.05231](https://arxiv.org/pdf/2403.05231)
- In additive manufacturing, self-supervised ViTs (MAE on thermal melt-pool images, SiT for LPBF anomalies) are used with fine-tuning to exploit unlabelled data — [arXiv 2411.12028](https://arxiv.org/pdf/2411.12028v2); [NIST listing](https://www.nist.gov/node/1852931)

### Inferences
- Cheapest experiment (about 1 day): extract frozen DINOv2 ViT-S/14 CLS (+ mean-patch) embeddings once for a subsample (e.g. 100–200k frames), cache them to disk, and train the 4×3 heads (linear or 1-hidden-layer MLP) on CPU or GPU in minutes. Use timm `vit_small_patch14_dinov2.lvd142m` or torch.hub `dinov2_vits14`. If this beats fine-tuned ResNet18 on unseen prints, as the LP vs FT evidence suggests it might, adopt LP-FT.
- VRAM estimate (inference, not measured): ViT-S/14 at 224 px gives 256 patch tokens. Forward-only fp16 at batch 64 should be well under 2 GB. Full fine-tuning at batch 32 with AMP plus gradient checkpointing should fit 4 GB. LoRA (via `peft`, rank 8 on qkv) further cuts optimizer state. Verify with `torch.cuda.max_memory_allocated()`; no measured number was found.
- ConvNeXt-T (~28M), EfficientNet-B0 and MobileNetV3 are plausible alternatives, but no OOD evidence specific to them was retrieved. Pick backbones on unseen-print validation balanced accuracy, not ImageNet accuracy.
- CLIP image encoders are also candidates for frozen probes. They were not researched here.

### Gaps
- No paper was found applying DINOv2/v3 or CLIP to FFF nozzle-camera images.
- No measured VRAM or FPS for ViT-S/14 training on 4 GB laptops was found.
- DINOv3 small-model availability and licence were not checked.

## Q6. Augmentation and resolution

### Takeaway
Evidence that augmentation plus pretraining makes ERM competitive is general, from WILDS-style studies. No domain-specific ablation for FFF was found. The current failure (print appearance: filament colour, lighting, geometry) argues for strong photometric augmentation, but some deviations may themselves change appearance (for example, hot-end temperature changing gloss).

### Cited Findings
- ERM with data augmentation is quite competitive with specialised DG algorithms on distribution-shift benchmarks — [arXiv 2205.12753](https://ar5iv.labs.arxiv.org/html/2205.12753)
- MixStyle synthesises new "styles" by mixing feature statistics across samples, which targets appearance shift — [arXiv 2104.02008](https://arxiv.org/abs/2104.02008v1)

### Inferences
- Recommended torchvision v2 pipeline (CPU cost only): RandomResizedCrop(224, scale=(0.6, 1.0), ratio about (0.9, 1.1)); ColorJitter(brightness 0.3, contrast 0.3, saturation 0.3, hue 0.5 to cover filament colour); RandomGrayscale(p=0.2); GaussianBlur(p=0.2); small RandomRotation (±10°). Horizontal flip is acceptable if the toolpath direction is not label-relevant. Avoid heavy scale changes, because extrusion width relative to the nozzle is the flow signal. Run an ablation per augmentation family on validation prints.
- Hue jitter with the full range (0.5), or random channel permutation, directly targets the "filament colour" confounder and costs nothing.
- Resolution 224 vs 320 px: at 320 px, activation memory rises about 2× ((320/224)² ≈ 2.04). That is feasible for ResNet18 on 4 GB with AMP. For ViT-S/14, use 224 (256 tokens) vs 322 (529 tokens); attention cost grows with the square of token count. No evidence was found that higher resolution helps cross-print generalisation; it is an inference that fine extrusion texture could benefit. Test it last.

### Gaps
- No FFF- or AM-specific augmentation ablation was found. The CAXTON augmentation recipe could not be read (nature.com blocked).

## Q7. Label noise / label lag and class imbalance

### Takeaway
Logit adjustment is a principled, nearly free fix for imbalance and targets balanced error directly. Label lag after a setpoint change is real physics (the melt flow and temperature respond over seconds), but no CAXTON-specific source quantifying it was retrieved. Drop transition frames using a lag window chosen on validation prints.

### Cited Findings
- Logit adjustment by label priors, applied post hoc (subtract τ·log π_y from the logits) or in the loss, is Fisher-consistent for minimising balanced error, unlike weight normalisation and several prior methods — [Menon et al., ICLR 2021 (arXiv 2007.07314)](https://arxiv.org/abs/2007.07314); [Google Research page](https://research.google/pubs/long-tail-learning-via-logit-adjustment)
- Balanced error averages per-class error, which avoids majority-class trivial solutions — [Menon et al.](https://arxiv.org/pdf/2007.07314)

### Inferences
- Imbalance: replace class-weighted CE with logit-adjusted CE per head (`logits + tau * log(prior)` during training, τ = 1). Alternatively, train plain CE and adjust post hoc on the calibration split. This adds no compute and can be swapped in.
- Label lag: build per-segment timestamps from the setpoint log and drop frames within N seconds after each change (sweep N ∈ {0, 1, 2, 4} s, choose on validation prints). Hot-end temperature probably needs a longer lag than flow or feed (thermal mass); a per-parameter N is reasonable. Alternatively, use soft labels that ramp from the old to the new class over the lag window. Inference: no source was found quantifying CAXTON response times. The setpoint-to-image mapping is setpoint metadata used only for labels, not model input, so it is consistent with ADR-0002.
- Balanced sampling (`WeightedRandomSampler` by class × print) also equalises print contributions, which may reduce dominance by prints with many frames.

### Gaps
- The CAXTON lag or transition handling and the physical response times for each parameter were not found. The search for "CAXTON lag" returned nothing relevant.

## Q8. Evaluation protocol

### Takeaway
DomainBed's central lesson is that model selection is part of the method: an algorithm without a specified selection protocol is incomplete, and oracle (test-domain) selection inflates results. For this project: grouped K-fold by print (and by part geometry if possible), select models on held-out validation prints within the training folds only, report test-fold numbers once, with bootstrap CIs over prints.

### Cited Findings
- DomainBed argues that a DG algorithm without a model-selection strategy is incomplete. It compares training-domain validation, leave-one-domain-out and oracle selection, and finds that tuned ERM matches the SOTA — [arXiv 2007.01434](https://arxiv.org/pdf/2007.01434)
- ERM averages differ by selection method (68.9 oracle, 67.0 training-domain, 63.8 leave-one-domain-out; secondary source) — [Liner review](https://liner.com/review/in-search-of-lost-domain-generalization)
- Averaging weights along the training path makes DG model selection more reliable (lower variance across checkpoints) — [EoA, NeurIPS 2022](https://proceedings.neurips.cc/paper_files/paper/2022/hash/372cb7805eaccb2b7eed641271a30eec-Abstract.html)
- Balanced error (mean per-class error) is the appropriate imbalance-robust metric — [Menon et al.](https://arxiv.org/abs/2007.07314)
- WILDS reports results across multiple seeds with ±std, and ID vs OOD gaps are large (Camelyon17 ERM 84.9 val vs 70.3 test) — [LISA table (arXiv 2201.00299)](https://arxiv.org/pdf/2201.00299)

### Inferences
- Use `sklearn.model_selection.StratifiedGroupKFold(groups=print_id)`. Inside each training split, hold out ~15% of prints as validation for early stopping, checkpoint and averaging choice, and τ, lag-N and temperature calibration. Never use test folds for these. This is consistent with the repo's fixed `data/splits/logo.json`.
- Metrics: per-head balanced accuracy and macro-F1 (4 numbers plus their mean), derived 9-way balanced accuracy for comparison with the 0.43/0.21 baseline, ECE after temperature scaling, and the seen-print vs unseen-print gap as the headline generalisation metric.
- Bootstrap CIs: resample prints (not frames) with replacement, 1000–2000 times, and recompute the metric each time. Frames within a print are highly correlated, so frame-level bootstrap gives far too narrow CIs. Report results over 3 seeds as well.
- Ablation discipline: change one factor at a time against the fixed ERM baseline. DomainBed shows most claimed gains vanish under equal tuning budgets, so give the baseline the same hyperparameter budget as each method.

### Gaps
- No AM-specific evaluation-protocol paper was found. Recommendations are carried over from the general DG literature.
