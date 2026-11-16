# CAXTON (Brion & Pattinson 2022) and the 2020–2026 literature on image-based in-situ FFF parameter/cause estimation

> **Access caveat (read first).** This session's network let me fetch only GitHub. nature.com, PMC, the Cambridge Apollo repository, ResearchGate, arXiv, matta.ai and publisher sites were all blocked by the proxy. So the findings below come from (a) the authors' **code and dataset README on GitHub**, which I read in full and treat as primary, and (b) **web-search snippets** of the paper and its follow-ups. I could not read the paper body, so several requested numbers (per-parameter accuracies, the correction-loop constants, the cross-printer test results) are listed under Gaps rather than guessed. Those hosts (www.nature.com, pmc.ncbi.nlm.nih.gov, www.repository.cam.ac.uk, arxiv.org) need to be allowed to close the Gaps.

## Q1. What exactly did Brion & Pattinson (2022) build, train and evaluate, and how was the data split?

### Takeaway
CAXTON trains one shared **Attention-56 residual attention network** with **four 3-way heads** (flow, lateral speed, Z offset, hotend) and a summed cross-entropy loss. Its input is a **320×320 crop centred on the nozzle tip, resized to 224**. The headline **84.3% average accuracy** comes from a **random image-level 70/20/10 split** (`torch.utils.data.random_split`), not from held-out prints. So that figure is not comparable to our leave-prints-out GroupKFold numbers. The paper's generalisation claims rest on **qualitative/online correction demos** on new parts, printers and materials, not on a held-out-print classification benchmark.

### Cited Findings
**Architecture (from code)**
- Backbone is `ResidualAttentionModel_56` "for input size 224 x 224": conv 7×7/2 (64) → maxpool → residual block (64→256) → **attention module stage 1** → residual block (256→512, stride 2) → **attention stage 2** → residual block (512→1024, stride 2) → **attention stage 3** → three residual blocks (1024→2048→2048→2048) → BN-ReLU-AvgPool(7) → 2048-d feature — [caxton/src/model/residual_attention_network.py](https://github.com/cam-cambridge/caxton/blob/main/src/model/residual_attention_network.py)
- Heads: the backbone `fc` is replaced by `nn.Identity()` and four separate `nn.Linear(2048, 3)` heads (`fc1..fc4`) are attached. The loss is `loss0+loss1+loss2+loss3`, each `F.cross_entropy` with no class weights. Optimiser is **AdamW, lr 1e-3**, with **ReduceLROnPlateau** (factor 0.1, patience 3, threshold 0.01) on val_loss — [caxton/src/model/network_module.py](https://github.com/cam-cambridge/caxton/blob/main/src/model/network_module.py)
- The paper describes the same design: "a single shared Attention-56 network backbone… followed by four separate fully connected output heads after the flattening layer, one for each parameter", each with three output neurons (low/good/high) — [Nature Commun. 2022 (search snippet)](https://www.nature.com/articles/s41467-022-31985-y); [Bohrium summary](https://www.bohrium.com/paper-details/generalisable-3d-printing-error-detection-and-correction-via-multi-head-neural-networks/817338338762555392-10026)
- The README says attention masks learn to focus on "the most recent extrusion", especially at attention module 2 — [caxton README](https://github.com/cam-cambridge/caxton)

**Input / crop / augmentation (from code)**
- Each 1280×720 RGB image is cropped to **320×320 centred on `nozzle_tip_x/y`** and resized to **224×224** — [DATASET_README](https://github.com/cam-cambridge/caxton/blob/main/DATASET_README.md); [src/data/dataset.py](https://github.com/cam-cambridge/caxton/blob/main/src/data/dataset.py)
- Pre-crop augmentation: `RandomRotation(10)` and `RandomPerspective(0.1, p=0.1)`. Post-crop: `RandomResizedCrop(224, scale=(0.9,1.0))`, `RandomHorizontalFlip`, `ColorJitter(brightness=0.1, contrast=0.1, saturation=0.1, hue=0.1)`, and normalisation with **dataset-specific** mean/std (e.g. full set mean [0.292, 0.270, 0.144], std [0.067, 0.069, 0.077], not ImageNet stats). An optional `per_img_normalisation` flag normalises each image by its own mean/std — [src/data/data_module.py](https://github.com/cam-cambridge/caxton/blob/main/src/data/data_module.py); [src/train_config.py](https://github.com/cam-cambridge/caxton/blob/main/src/train_config.py)
- Batch size 32, max 50 epochs, 2 GPUs (DDP) — [src/train_config.py](https://github.com/cam-cambridge/caxton/blob/main/src/train_config.py)
- Hardware: Ubuntu 18.04, i9-9900K, 64 GB RAM, **2× Quadro RTX 5000**. Inference takes **~0.07 s per image** at batch size 1 — [caxton README](https://github.com/cam-cambridge/caxton)

**Training stages / dataset variants**
- The config has three dataset CSVs: `dataset_single_layer` (`caxton_dataset_filtered_single.csv`), `dataset_full` (`caxton_dataset_filtered.csv`) and `dataset_equal` (`caxton_dataset_filtered_equal.csv`, presumably class-balanced) — [src/train_config.py](https://github.com/cam-cambridge/caxton/blob/main/src/train_config.py)
- The paper found "splitting the training process into three separate stages and using transfer learning was the most robust". The best seed from each stage seeded the next, and the final stage retrained the best-seed model "on the full dataset containing images for all 3D geometries" — [Nature Commun. 2022 (search snippet)](https://www.nature.com/articles/s41467-022-31985-y)
- The README says the three-stage transfer learning "is not necessary and training can be completed in an end-to-end fashion with a single training regime" — [caxton README](https://github.com/cam-cambridge/caxton)

**Dataset facts**
- **8× Creality CR-20 Pro** printers with **Logitech C270** webcams aimed at the nozzle; **PLA only**, many colours; 192 prints of STLs scraped from the web and sliced with randomised rotation, scale, infill pattern/density and perimeters. G-code was split into ≤2.5 mm moves for fast parameter updates. Parameters were re-sampled uniformly every **150 images**. Automatic part removal let the fleet run continuously — [DATASET_README](https://github.com/cam-cambridge/caxton/blob/main/DATASET_README.md)
- 1,272,465 images (1,272,273 labelled). Prints 183–191 (large failures, poor lighting) were excluded from parameter prediction. The `_classification3` CSVs bin each parameter into low/good/high. The `_gaps` CSV **drops 15 images (~6 s) after each parameter change** because of software and mechanical lag before the change becomes visible — [DATASET_README](https://github.com/cam-cambridge/caxton/blob/main/DATASET_README.md)
- Label-noise notes from the authors: flow and feed labels are "very reliable" but have an unquantified offset (99% ≈ 100%; 30 vs 35 mm/s look alike). **Z offset is "the most noisy labelled parameter"**: printers drifted and were recalibrated many times, probe noise, and values < 0.08 mm are mislabelled and should be ignored. Hotend temperature is roughly Gaussian around 205 °C because low-temperature prints often failed outright; it spans 160–250 °C. Flow and feed span roughly 20–200%, and Z roughly −0.08 to 0.32 mm. Images "can vary considerably depending on lighting conditions and the lateral speed of the print head" — [DATASET_README](https://github.com/cam-cambridge/caxton/blob/main/DATASET_README.md)
- Paper/repository counts: ~1.2 M images. One listing gives a pre-filtered CSV of 948,396 images (failures, outliers, dark images and post-change frames removed). A snippet cites 1,166,552 images after manual removal — [search summary of Apollo record](https://www.repository.cam.ac.uk/items/6d77cd6d-8569-4bf4-9d5f-311ad2a49ac8). These counts conflict, probably because they come from different filter stages.

**Split protocol and accuracy**
- `setup()` uses `torch.utils.data.random_split(self.dataset, [0.7N, 0.2N, rest])` over **individual images**. No grouping by `print_id` exists anywhere in the data module — [src/data/data_module.py](https://github.com/cam-cambridge/caxton/blob/main/src/data/data_module.py)
- Reported result: the network predicts all four parameters "with an average accuracy of 84.3%" — [caxton README](https://github.com/cam-cambridge/caxton). This is a **random-image-split** test accuracy.
- Frames come at ~2.5 fps (15 images ≈ 6 s, and timestamps in `print_log_full.csv` are ~0.46 s apart) and parameters are held constant for 150 frames. So a random image split puts near-duplicate neighbouring frames of the same print and parameter block in both train and test — [DATASET_README](https://github.com/cam-cambridge/caxton/blob/main/DATASET_README.md)

**Generalisation claims**
- The authors claim the method can "identify and correct errors in unfamiliar objects or materials, or even on new printing systems" and works "across many geometries, materials and even different 3D printing setups" — [Cambridge press release](https://www.cam.ac.uk/research/news/algorithm-learns-to-correct-3d-printing-errors-for-different-parts-materials-and-systems)
- The paper itself notes that "the performance of existing error correction methods on unseen objects is unclear", and it motivates the work on that gap — [Nature Commun. 2022 (search snippet)](https://www.nature.com/articles/s41467-022-31985-y)
- A paper figure is titled "Printer and feedstock agnostic online parameter correction and discovery" — [ResearchGate figure page](https://www.researchgate.net/figure/Printer-and-feedstock-agnostic-online-parameter-correction-and-discovery-a-Rapid_fig4_362705879)
- The project blog says it was tested on ABS-X, a material absent from the PLA-only training set — [matta.ai blog (search snippet)](https://matta.ai/research/generalisable-3d-printing-error-detection-and-correction)
- In non-thermoplastic tests the network "often reduced the flow rate and, for the first layer, lowered the Z offset" for over-extruding materials such as mayonnaise and ketchup. It also corrected several incorrect parameters introduced mid-print — [Nature Commun. 2022 (search snippet)](https://www.nature.com/articles/s41467-022-31985-y)

### Inferences
- **Our 0.43 (shared prints) vs 0.21 (unseen prints) balanced accuracy matches what CAXTON's protocol would hide.** CAXTON's 84.3% is a leakage-prone random-frame split (temporal neighbours in train and test). No held-out-print classification number was published to compare against. Our GroupKFold result is a stricter and more honest benchmark, not evidence that we did worse than CAXTON.
- Differences between their setup and ours that plausibly matter:
  - **Factorised 4×3 heads vs our 9-way single-cause softmax.** CAXTON varies all four parameters at once, so a frame often has several non-"good" labels. A single-cause softmax throws that away and forces mutually exclusive classes.
  - **Dataset-specific normalisation** (and an optional per-image normalisation) instead of ImageNet stats.
  - **Rotation/perspective/colour augmentation** around the nozzle.
  - **Dropping post-change frames (`_gaps` CSV).**
  - A **staged curriculum** (single-layer → full).
- The `dataset_equal` CSV suggests they also tried a class-balanced subset. I could not confirm whether the 84.3% model used it; the config default is `dataset_full`.
- Z-offset labels are by the authors' own account the noisiest, and hotend has the narrowest real spread. Per-parameter ceilings will therefore differ, and macro-averaging across parameters hides that.

### Gaps
- Per-parameter test accuracies (flow, speed, Z, hotend), per-stage results, and whether any held-out-print or held-out-geometry quantitative test exists in the paper or SI. The paper body was unreachable (nature.com and PMC blocked).
- The exact contents of the three training stages, e.g. whether stage 1 is single-layer only and stage 2 a subset. The snippet confirms only three stages with best-seed transfer and a final full-dataset stage.
- Which other printers and materials were tested, and with what quantitative outcome. Only "ABS-X", "printer and feedstock agnostic" and the mayonnaise/ketchup demos are confirmed.

## Q2. How did the real-time correction loop work?

### Takeaway
The confirmed facts are the hardware and the cadence: webcam at ~2.5 fps, G-code split into ≤2.5 mm segments so updates take effect quickly, ~0.07 s per inference on a workstation GPU. The controller aggregated several predictions before acting, and the 2022 follow-up (Fast-CAXTON) reports that the earlier system was more than 4× slower than its own ~15 Hz. I could not verify the exact aggregation window, thresholds or update magnitudes.

### Cited Findings
- G-code was split into moves ≤2.5 mm "to reduce response times when updating printing parameters during a print" — [DATASET_README](https://github.com/cam-cambridge/caxton/blob/main/DATASET_README.md)
- Parameter changes take ~6 s (15 frames) to show up in steady state, because of "software and mechanical delays" — [DATASET_README](https://github.com/cam-cambridge/caxton/blob/main/DATASET_README.md)
- Inference takes ~0.07 s per sample at batch 1 on an RTX 5000-class GPU — [caxton README](https://github.com/cam-cambridge/caxton)
- The system corrected several incorrect parameters introduced mid-print. A high Z offset could be fixed by lowering Z offset and/or raising flow (a many-to-one cause→correction mapping) — [Nature Commun. 2022 (search snippet)](https://www.nature.com/articles/s41467-022-31985-y)
- Fast-CAXTON (Brion & Pattinson, *Advanced Intelligent Systems* 2022, doi 10.1002/aisy.202200153) reports that its combined control system "ran at sampling rates of nearly 15 Hz, over 4 times faster than the previous state of the art" — [Wiley/DOAJ record](https://doaj.org/article/9bd52b3579b64e408bd7a29de2e5454c); [fast-caxton README](https://github.com/cam-cambridge/fast-caxton)

### Inferences
- Because a parameter change needs ~6 s to show, any controller on this data must smooth over many frames, e.g. a majority/mode or mean-probability window over several seconds. It also needs a refractory period after each correction, or it will over-correct while the old state is still visible. This fits our `gate()` design.
- "Over 4× slower than ~15 Hz" puts the original CAXTON loop at roughly ≤3.5 Hz, which agrees with the ~2.5 fps capture.

### Gaps
- The exact aggregation rule (window length, mode vs averaging, confidence thresholds), the step sizes per parameter, and whether hotend corrections were enabled online. These are in the paper's Methods, which I could not reach.
- End-to-end latency figures and the edge hardware used (Raspberry Pi/OctoPrint vs workstation) for the 2022 loop.

## Q3. Follow-up work by the same group (Brion, Pattinson, Margadji; Cambridge / Matta)

### Takeaway
The group moved from **classification** to **continuous regression of flow rate** (Fast-CAXTON: RegNet, ~250k images, ~15 Hz). It then moved to **uncertainty-aware active learning on top of a pretrained "foundation" extrusion model** that improves across repeated builds of the same part (Iterative Learning, *Additive Manufacturing* 2024), and to **LLM/VLM-style hybrid reasoning** for explanation and action (arXiv 2506.08462, 2025). Each step signals that one frozen per-frame classifier does not by itself transfer to new parts: they either narrow the target (one parameter, regression) or adapt online to the specific part.

### Cited Findings
- **Fast-CAXTON (2022)**, "Quantitative and Real-Time Control of 3D Printing Material Flow Through Deep Learning", *Adv. Intell. Syst.* Firmware metadata plus real-time video produced a new dataset of **>250,000 automatically labelled images**. **Vision regression** models predict material flow as a continuous variable. The loop runs at **~15 Hz**, "over 4 times faster than the previous state of the art", and can "learn optimal parameters for unseen complex materials, and achieve rapid error correction on new parts" — [DOAJ record](https://doaj.org/article/9bd52b3579b64e408bd7a29de2e5454c); [AMiner](https://www.aminer.org/pub/631ec10590e50fcafd7911f4/quantitative-and-real-time-control-of-d-printing-material-flow-through-deep)
- The Fast-CAXTON repo trains "a **regnet** neural network to quantitatively predict with regression the relative state of the material flow rate in real time… from a single input image" (PyTorch 1.10.1) — [fast-caxton README](https://github.com/cam-cambridge/fast-caxton)
- **Iterative learning for efficient additive mass production**, Margadji, Brion & Pattinson, *Additive Manufacturing* 2024, doi 10.1016/j.addma.2024.104271. A vision-based control system for material extrusion "coupling active learning and uncertainty awareness with a foundation model" starts from general extrusion knowledge, collects data where it is least certain, and improves over repeated builds of the same part — [Bohrium](https://www.bohrium.com/paper-details/iterative-learning-for-efficient-additive-mass-production/1039012345717719069-3788); [matta.ai summary](https://matta.ai/research-publications/iterative-learning-for-mass-production); [author PDF (search snippet)](https://cemag1.github.io/assets/papers/Iterative_learning%20for_efficient_additive_mass_production.pdf)
- **Hybrid Reasoning for Perception, Explanation, and Autonomous Action in Manufacturing**, Margadji & Pattinson, arXiv 2506.08462 (2025). A vision-language-action approach pairs engineering knowledge with perception — [arXiv](https://arxiv.org/pdf/2506.08462); [matta.ai resources](https://matta.ai/resources)
- Not from the group but related: **LLM-3D Print** (arXiv 2408.14307) uses GPT-4o-style LLM agents to monitor layer images and correct FFF defects. Authorship is not Cambridge, per the search — [arXiv](https://arxiv.org/html/2408.14307v2)

### Inferences
- The group's own direction (regression of one parameter; per-part online adaptation with uncertainty; language-model reasoning layered on perception) suggests the field does not treat zero-shot cross-part cause classification as solved. Uncertainty-gated abstention and adaptation to the specific part are their answers to the generalisation gap.

### Gaps
- Quantitative results of the Iterative Learning paper (error reduction per build cycle, backbone used for the "foundation model", ViT or CNN) and of arXiv 2506.08462. The full texts were unreachable.
- Whether Fast-CAXTON reports a held-out-print regression error, and its split protocol. Its code was not inspected beyond the README.

## Q4. Other 2020–2026 image-based in-situ FFF parameter / defect-cause estimation works

### Takeaway
Most comparable works are smaller, single-printer studies of extrusion state (under/over-extrusion) with nozzle or layer cameras. They report high accuracies, but on random or unspecified splits. I found **no study that reports a leave-prints-out / held-out-geometry accuracy on CAXTON**, and no FFF image study that quantifies a cross-part accuracy drop.

### Cited Findings
- **Jin, Zhang & Gu (2020)**, "Autonomous in-situ correction of fused deposition modeling printers using computer vision and deep learning", *Manufacturing Letters* 22. A nozzle-camera CNN classifies extrusion state and drives in-situ correction — [citation in arXiv 2510.24994](https://arxiv.org/pdf/2510.24994v1). The same group's 2020 Wiley paper uses a real-time camera plus deep learning for interlayer defects such as delamination and warping — [search snippet, PolyU record](https://ira.lib.polyu.edu.hk/handle/10397/116097). (Accuracy and split not retrieved.)
- **Lee et al. (2023, Adv. Intell. Syst.)**: deep-learning computer vision corrects under- and over-extrusion in FDM. A related entry reports in-situ correction cut **yield-strength variance six-fold** — [DOAJ record](https://doaj.org/article/92411f84876c4e2ca951bbae1791aa45)
- **Zhang et al. (2025, Virtual and Physical Prototyping)**: YOLO object detection for in-situ monitoring of printed line morphology — [search snippet via arXiv 2510.24994](https://arxiv.org/pdf/2510.24994v1)
- **Online detection and closed-loop correction of stringing defects in FFF using a mixed-input multi-head network** (*Progress in Additive Manufacturing*, 2026) is a direct descendant of the CAXTON multi-head idea that mixes image and process inputs — [Springer](https://link.springer.com/article/10.1007/s40964-026-01942-y). (Details not retrieved. Note: mixing in process inputs would break our ADR-0002.)
- **Caxton-S**: a semantically re-labelled derivative of CAXTON with six semantic defect classes on Kaggle. Its split protocol was not found — [Kaggle](https://www.kaggle.com/datasets/adritganeriwala/caxton-s-semantic-3d-printing-defect-dataset)
- **Fu et al. (2021, Additive Manufacturing 38, 101749)**: in-situ FFF monitoring — [PDF](https://cse.sc.edu/~adowney2/publications/Journal_publications/Fu_2021_In_situ_monitoring/Fu_2021_In_situ_monitoring.pdf). Review: "In situ monitoring for fused filament fabrication process: A review" — [ResearchGate](https://www.researchgate.net/publication/347740353_In_situ_monitoring_for_fused_filament_fabrication_process_A_review). Review: "Sensor-Based and Computational Methods for Error Detection and Correction in 3D Printing" (2024) — [ResearchGate](https://www.researchgate.net/publication/384036538_Review-Sensor-Based_and_Computational_Methods_for_Error_Detection_and_Correction_in_3D_Printing)
- **Adjacent, transferable protocol (metal PBF)**: a 2024 pore-location segmentation study explicitly tests generalisation across **different geometric cross-sections** — [arXiv 2408.02507](https://arxiv.org/pdf/2408.02507)
- **Adjacent evidence for a print-to-print gap**: a 2026 tactile-texture dataset of 3D prints found classifiers reached up to **70.66% on unseen prints** when trained on high-fidelity resin prints, versus **~31%** when trained on high-variance Ender-3 FFF output. Print-to-print variance in FFF output alone caused a large accuracy collapse (a different task, but the same mechanism) — [arXiv 2606.25886 (search summary)](https://arxiv.org/pdf/2606.25886)

### Inferences
- Without a published held-out-print baseline on CAXTON, our GroupKFold 0.21 balanced-accuracy result (9 classes → chance ≈ 0.11) may itself be one of the more rigorous numbers available. The report should state the protocol explicitly and not compare against 84.3% as though like-for-like.

### Gaps
- Accuracies and split protocols for Jin et al. 2020, Lee et al. 2023, the 2026 stringing paper, and any CAXTON-benchmark papers (Google Scholar "cited by" was not reachable).
- Temporal/video models (e.g. 3D-CNN or frame-stack on nozzle video) and explicit cross-printer domain-generalisation studies for FFF: none surfaced in my searches.

## Q5. Explicit evidence on the cross-part/cross-print gap and techniques to close it

### Takeaway
Direct quantitative evidence on CAXTON is missing. The authors and data card do document the mechanisms behind the gap: temporal autocorrelation, per-print lighting and colour, print-head speed blur, Z drift between recalibrations, and a ~6 s lag after each change. The techniques they and their follow-ups use are: nozzle-centred cropping, rotation/perspective/colour augmentation, dataset/per-image normalisation, removal of transition frames, factorised per-parameter heads, staged training, multi-frame aggregation in control, and later uncertainty-aware online adaptation.

### Cited Findings
- Sources of nuisance variation named by the authors: lighting and lateral head speed change image appearance a lot; the prints are "a wide range of colours"; Z calibration "tends to drift during repeated use" and was recalibrated many times — [DATASET_README](https://github.com/cam-cambridge/caxton/blob/main/DATASET_README.md)
- Transition-frame removal: drop 15 frames (~6 s) after each change — [DATASET_README](https://github.com/cam-cambridge/caxton/blob/main/DATASET_README.md)
- Invariance tooling in code: rotation ±10°, perspective, flip, colour jitter, optional per-image normalisation — [src/data/data_module.py](https://github.com/cam-cambridge/caxton/blob/main/src/data/data_module.py); [src/data/dataset.py](https://github.com/cam-cambridge/caxton/blob/main/src/data/dataset.py)
- Online adaptation with uncertainty and active learning across builds — [matta.ai summary of Margadji et al. 2024](https://matta.ai/research-publications/iterative-learning-for-mass-production)

### Inferences (for the team's model and protocol choice)
- **Formulation:** replace the 9-way single-cause softmax with **4 independent 3-way heads** (CAXTON's formulation), or with 4 ordinal/regression heads (the Fast-CAXTON direction). Derive the "cause" afterwards from the per-parameter posteriors. This matches the label structure, since several parameters deviate at once.
- **Data hygiene:** train and evaluate on the `_gaps` (post-change-trimmed) labels. Drop Z < 0.08 mm and prints 183–191. Consider dataset-mean or per-image normalisation and CAXTON's augmentation set.
- **Protocol:** keep leave-prints-out GroupKFold and report both splits side by side. Also report a **block-level metric** that aggregates over each 150-frame constant-parameter block (or a sliding window). Control acts on aggregates, and frame-level accuracy understates what is usable. Report per-parameter balanced accuracy, because Z and hotend have different noise and range.
- **Robustness:** abstain on low confidence, since gate() can refuse. This mirrors the group's later uncertainty-aware direction.

### Gaps
- No source found that quantifies CAXTON accuracy on held-out prints, other printers, or other cameras. No published technique has been shown, with numbers, to close the cross-print gap on this dataset.
