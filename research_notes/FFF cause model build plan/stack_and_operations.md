# Tech stack and MLOps-light operational chain for an image-based FFF process-cause model (small UG team, Windows laptops, RTX 3050/4050)

Scope: data -> versioning -> training -> evaluation -> registry/packaging -> edge runtime -> explanation/early-warning -> monitoring/drift -> retraining. Context: Python 3.11, PyTorch, uv, pytest, SQLite event store, Streamlit dashboard, pure-Python safety gate, OctoPrint-style interface, CAXTON (~1M JPEGs, ~55 GB zips, 125 MB label CSV), currently ~80k-image subset. Latency budget: cause model + conformal + gate <= 30 ms p95/event; proactive per-frame inference ~2.5 fps (400 ms/frame budget).

Note on sources: about 20 searches. Official docs were found for SQLite WAL, PyTorch reproducibility/AMP, ONNX Runtime DirectML/TensorRT EPs, MLflow backend stores, Streamlit fragments, Google MLOps maturity levels, the model-cards paper, the hidden-technical-debt paper, alibi-detect MMD and a 2024 drift-tool comparison. **No reliable published latency figures were found for ResNet18/ConvNeXt-T/DINOv2-S/EfficientNet at 224 px on RTX 3050-class laptop GPUs.** Those must be measured locally (see Gaps).

---

## 1. Data pipeline and versioning (80k to 1M images on a laptop)

### Takeaway
For a 2-3 person team on Windows, a **plain hashed manifest committed to git** (CSV/Parquet of `path, sha256, print_id, labels, split`, plus a top-level dataset hash) is enough and adds no dependency. Add DVC only if the team needs to share the data cache through a remote. Git LFS is a poor fit for ~1M small files. For speed, **pre-crop to the nozzle ROI once, resize to training resolution, and pack into ~100-500 MB tar shards (WebDataset format)** or cache backbone features to `.npy`. That removes the small-file and JPEG-decode bottleneck on laptop SSDs.

### Cited Findings
- Git LFS stores pointer files in git and the content on the hosting server, needs an LFS server that not every host provides, and ties storage to the git host. DVC adds data versioning on top of git and supports arbitrary remotes (S3 etc.) — [Censius DVC vs Git-LFS](https://censius.ai/blogs/dvc-vs-git-and-git-lfs-in-machine-learning-reproducibility); [lakeFS comparison](https://lakefs.io/blog/dvc-vs-git-vs-dolt-vs-lakefs/)
- Vendor benchmark (Oxen, a competitor, so read with care) at ImageNet scale: DVC is faster than Git LFS but needs more commands. Git LFS add/commit is slow because of its hashing and file copying — [Oxen 1M-files benchmark](https://docs.oxen.ai/features/performance)
- DVC checksums files locally, which can be slow for large datasets — [Reintech DVC vs LFS vs lakeFS](https://reintech.io/blog/dvc-vs-git-lfs-vs-lakefs-ml-data-versioning)
- A single-author benchmark (100 GB of 10 MB JPEGs) reports DVC 3.0 pushing in 4m12s vs Git LFS 3.0 in 5m23s. It is unverified — [DEV Community](https://dev.to/johalputt/benchmark-dvc-30-vs-git-lfs-30-vs-s3-2026-for-storing-100gb-ml-datasets-15fg)
- Worked CV example of using DVC for image data versioning — [Alex Strick van Linschoten](https://alexstrick.com/posts/2022-05-24-data-versioning-dvc.html)
- WebDataset stores datasets as POSIX tar archives of the original files, implements PyTorch `IterableDataset`, and works with existing DataLoader code. Its authors claim about a 10x I/O improvement on hard drives over random-access file datasets — [PyTorch blog: Efficient PyTorch I/O library](https://pytorch.org/blog/efficient-pytorch-io-library-for-large-datasets-many-files-many-gpus/)
- Google Cloud reported a 6x overall speedup with WebDataset plus DDP, reading from Cloud Storage. That number depends on the setup — [Google Cloud blog](https://cloud.google.com/blog/products/ai-machine-learning/efficient-pytorch-training-with-vertex-ai)
- Very small shards bring back the small-file problem. Shard counts should divide evenly across workers, because WebDataset is not built for skip-index reads — [zeroentropy streaming datasets](https://www.zeroentropy.dev/concepts/streaming-datasets/); [HF forum](https://discuss.huggingface.co/t/loading-webdatasets-across-multiple-nodes/88276)
- Datasheets/model-card practice: the documentation should record intended use, evaluation procedure and context — [Mitchell et al., Model Cards for Model Reporting](https://arxiv.org/abs/1810.03993)
- "Data dependencies" and "changes in the external world" are named ML technical-debt risk factors, which supports pinning data versions explicitly — [Sculley et al., Hidden Technical Debt in ML Systems](https://papers.nips.cc/paper/5656-hidden-technical-debt-in-machine-learning-systems)

### Inferences
- **Recommended chain:** (1) the raw CAXTON zips stay read-only on disk. (2) A `prepare_data.py` step extracts the 500/print subset, crops to the nozzle ROI, resizes (for example to 256 px short side), and re-encodes as JPEG q~90. That shrinks 55 GB by an order of magnitude and removes decode cost at train time. (3) Write ~100-500 MB tar shards grouped **by print** so leave-one-group-out splits map to whole shards. (4) Emit `data/manifest.parquet` with per-file sha256 and a single `dataset_sha` (hash of the sorted manifest). Commit the manifest, not the images. (5) Write a short `DATASHEET.md` covering source and licence, the subsetting rule, crop parameters, label-CSV hash and known label noise.
- For ~80k images at 224 px, an alternative to shards is **cached frozen-backbone features** (`.npy` memmap, e.g. 80k x 384 float16 ≈ 61 MB for DINOv2-S CLS). This makes linear/MLP-head experiments run in seconds on CPU and fits the 4 GB VRAM limit.
- FFCV and DALI are not recommended. FFCV's Windows support is poor and DALI is Linux-first; neither was checked in this research (see Gaps). LMDB works on Windows but adds a dependency that a tar or npy cache doesn't need.
- DVC is worth adding only if a shared remote (a Google Drive or university S3 bucket) is needed. Its manifest (`.dvc` files) then replaces the hand-rolled manifest. The hashed-manifest approach is a strict subset of what DVC does and can be swapped in later.

### Gaps
- No found benchmark of WebDataset vs folder-of-JPEGs on a Windows laptop NVMe. Measure images/s with `--limit`.
- FFCV/DALI Windows support was not verified in this pass.
- CAXTON's licence and terms for redistributing derived shards were not checked.

---

## 2. Training and experiment tracking (4 GB VRAM)

### Takeaway
Use **plain PyTorch plus timm backbones**, **AMP (`torch.autocast("cuda")` + `torch.GradScaler("cuda")`)**, small batches with gradient accumulation, and a frozen-or-partially-frozen backbone. Track experiments with **one JSON/JSONL record per run** (config, git SHA, dataset_sha, seed, metrics) and optionally TensorBoard. Add MLflow with a local SQLite backend only if a UI or registry is wanted. Keep YAML configs loaded into a typed dataclass. Hydra is unnecessary at this scale. Seed everything and record determinism flags. Full bitwise determinism on GPU costs speed and isn't required if the seeds and data hashes are logged.

### Cited Findings
- The current AMP API is `torch.autocast("cuda", ...)` and `torch.GradScaler("cuda", ...)`. The `torch.cuda.amp.*` forms are being deprecated. Autocast and the scaler are modular — [PyTorch AMP docs](https://pytorch.org/docs/stable/amp)
- FP16 tensors use half the memory of FP32, which allows larger batches. Savings depend on which activations are actually cast (non-official mirror) — [Mintlify PyTorch mixed precision](https://www.mintlify.com/pytorch/pytorch/advanced/mixed-precision)
- Reproducibility: `torch.manual_seed`, plus separate NumPy and Python `random` seeds. `cudnn.benchmark=True` may pick different algorithms on each run. `cudnn.deterministic=True` affects only cuDNN. `torch.use_deterministic_algorithms(True)` is the broad switch: it raises on non-deterministic ops, and it is slower. With CUDA ≥10.2 you need `CUBLAS_WORKSPACE_CONFIG` — [PyTorch Reproducibility notes](https://docs.pytorch.org/docs/stable/notes/randomness.html)
- MLflow's Model Registry requires a database-backed store. SQLite qualifies, and the current default is `sqlite:///mlflow.db`. The legacy `./mlruns` file store is in maintenance mode. SQLite is suited to a single user or local use — [MLflow backend stores](https://mlflow.org/docs/latest/self-hosting/architecture/backend-store/)
- timm ships a `benchmark.py` that measures inference/train throughput per model and writes CSV/JSON — [timm benchmark.py](https://www.github.com/rwightman/pytorch-image-models/blob/master/benchmark.py)
- Configuration issues are a named ML technical-debt category — [Sculley et al.](https://papers.nips.cc/paper/5656-hidden-technical-debt-in-machine-learning-systems)

### Inferences
- Lightning adds abstraction and a dependency without much gain for a single-GPU classifier. A ~150-line plain training loop is easier to test with pytest and to read.
- 4 GB VRAM recipe: AMP; batch 32-64 at 224 px for ResNet18 or EfficientNet-B0; batch 16-32 plus `accumulate=2-4` for ConvNeXt-T; `channels_last`; freeze early stages or train a head on cached DINOv2-S features first; gradient checkpointing (`torch.utils.checkpoint`) only if a full fine-tune of ConvNeXt-T or ViT-S OOMs. These batch sizes are engineering estimates, not cited; confirm with `torch.cuda.max_memory_allocated()`.
- Tracking: W&B is cloud-first, and its free tier has account and terms considerations. MLflow and TensorBoard are local and free. A `runs/<timestamp>_<sha>/run.json` plus `metrics.jsonl` is enough for pre-registered selection and can be read by the Streamlit dashboard and by tests. Write MLflow optionally from the same record.
- Each run record should hold `git_sha`, `git_dirty`, `dataset_sha`, `labels_csv_sha256`, `split_file_sha256` (e.g. `logo.json`), `config` (resolved), `seed`, `torch/cuda/timm versions`, `gpu_name`, `cudnn.benchmark`/`deterministic` flags, and wall time.

### Gaps
- No measured VRAM figures were found for timm backbones at 224 px under AMP on 4 GB cards. Measure them.
- Gradient checkpointing docs and memory/speed trade-off numbers weren't retrieved.

---

## 3. Evaluation harness

### Takeaway
Use **leave-one-print/group-out (grouped) CV** with a frozen split file, **bootstrap CIs resampled by group** (print), a **pre-registered selection rule** written before test folds are scored, **golden-fixture tests** (a few fixed crops with expected logits and class within tolerance, checked for both the PyTorch and ONNX paths), and a **one-to-two-page model card** per released model.

### Cited Findings
- Model cards are short (1-2 page) documents covering intended use, evaluation procedure, and performance disaggregated across relevant conditions — [Mitchell et al. 2019](https://arxiv.org/abs/1810.03993); [Google Research page](https://research.google/pubs/model-cards-for-model-reporting/)
- Google's MLOps Level 1 adds automated **data validation and model validation** steps before deployment — [Google Cloud MLOps: continuous delivery and automation pipelines](https://docs.cloud.google.com/architecture/mlops-continuous-delivery-and-automation-pipelines-in-machine-learning)

### Inferences
- Bootstrap: resample prints (groups), not frames. Frames within a print are highly correlated, so frame-level bootstrap would give CIs that are too narrow. 1,000-2,000 resamples, percentile CI. Report macro-F1 and per-class recall with CIs.
- Pre-registration: commit `eval/selection_rule.md` (metric, tie-break, minimum CI lower bound) before scoring the test folds. The selection script reads only validation-fold metrics and errors if test metrics are requested before a model is chosen.
- Golden fixtures: store ~10 crops plus `expected.json` (class, top-1 prob ±1e-3 for FP32, ±1e-2 for FP16/ONNX). Mark them `slow` or `gpu` as appropriate. This catches preprocessing drift, such as RGB/BGR, normalisation or resize interpolation, between training and runtime. That is the most common silent failure when exporting.
- Conformal calibration should use a held-out calibration split, grouped by print. Report empirical coverage per class (Mondrian) together with mean set size.

### Gaps
- No primary source on group bootstrap specifics was retrieved. This is standard statistics practice, but it should be cited from a stats text if needed for the report.

---

## 4. Model registry and packaging; export and runtime choice

### Takeaway
For a 2-3 person team, the **"registry" can be a directory convention**: `models/<name>/<version>/{model.pt (state_dict + metadata dict), model.onnx, model_card.md, calib.json (conformal thresholds), golden/expected.json, run.json}` plus a `models/REGISTRY.json` pointing to `current`. MLflow's registry is a fine optional upgrade, and SQLite-backed MLflow works locally. Export to **ONNX** and run with **ONNX Runtime CUDA EP** (or the TensorRT EP with FP16 and engine cache) on NVIDIA laptops. Keep the **PyTorch model for Grad-CAM** in the explanation worker, because CAM needs gradients and activations that an inference-only ONNX graph doesn't expose.

### Cited Findings
- MLflow Model Registry needs a DB-backed store. SQLite works and is suited to single-user or local use — [MLflow backend stores](https://mlflow.org/docs/latest/self-hosting/architecture/backend-store/)
- ONNX Runtime **DirectML EP**: Windows GPU backend over DirectX 12, works across vendors, needs Windows 10 1903+, ships as `onnxruntime-directml`. It **does not support memory-pattern optimisation or parallel execution, so it does not support multi-threaded `Run` calls on the same session**. DirectML is in sustained engineering, with new development moved to Windows ML — [ORT DirectML EP docs](https://onnxruntime.ai/docs/execution-providers/DirectML-ExecutionProvider.html); [microsoft/windowsml](https://github.com/microsoft/windowsml); [Windows ML supported EPs](https://learn.microsoft.com/en-in/windows/ai/new-windows-ml/supported-execution-providers)
- ONNX Runtime **TensorRT EP**: configured through provider options such as `trt_fp16_enable`, `trt_engine_cache_enable` and `trt_engine_cache_path`. The env-var approach is deprecated. FP16 must be enabled explicitly. Engine caches are not portable across GPUs. It installs via `onnxruntime-gpu` with TensorRT installed separately — [ORT TensorRT EP docs](https://onnxruntime.ai/docs/execution-providers/TensorRT-ExecutionProvider.html); [NVIDIA blog: CUDA and TensorRT EPs in ONNX Runtime](https://developer.nvidia.com/blog/end-to-end-ai-for-nvidia-based-pcs-cuda-and-tensorrt-execution-providers-in-onnx-runtime/)
- Get-started for ORT on Windows — [onnxruntime.ai with-windows](https://onnxruntime.ai/docs/get-started/with-windows.html)
- Latency data points found (none on RTX 3050):
  - RTX 4050 blog: ResNet18 ~34 ms/batch in PyTorch eager, ~26 ms with `torch.compile(mode="max-autotune")`, and ORT ~302 ms in that author's setup, which is likely a misconfigured ORT (CPU EP or no IO binding). The batch size was not given. Treat as anecdotal — [Towards AI: PyTorch, ONNX, TensorRT explained](https://pub.towardsai.net/deep-learning-inference-pytorch-onnx-and-tensorrt-explained-0850d6c794f1)
  - ResNet-18 FP16 vs FP32 on T4: 3.83x speedup (relative only) — [arXiv 2604.14552](https://arxiv.org/pdf/2604.14552)
  - RTX 3060 12 GB, PyTorch eager, ConvNeXt-Tiny 224 px, batch 96: ~1,120 img/s (blog, unverified; throughput not latency) — [SpecPicks](https://specpicks.com/blog/best-budget-gpu-cnn-computer-vision-inference-rtx-3060-12gb-2026)
  - Community timm latency CSV on RTX A6000 (FP32, 2023) — [kentaroy47/timm_speed_benchmark](https://awesome.ecosyste.ms/projects/github.com%2Fkentaroy47%2Ftimm_speed_benchmark)
- pytorch-grad-cam supports CNNs and ViTs. For ViT the target layer is `model.blocks[-1].norm1` with a `reshape_transform`. The model's forward must return a tensor, so dict or tuple outputs need a wrapper. The tutorials cover ResNet, ConvNeXt, ViT and Swin — [grad-cam on PyPI](https://pypi.org/project/grad-cam/1.5.0); [pytorch-gradcam-book](https://jacobgil.github.io/pytorch-gradcam-book/introduction.html); [HF recipes](https://jacobgil.github.io/pytorch-gradcam-book/HuggingFace.html)

### Inferences
- Latency: a single 224 px image through ResNet18 or EfficientNet-B0 or ConvNeXt-T on an RTX 3050 laptop GPU is very likely a few milliseconds in FP16 (an engineering expectation, not a cited figure). The 30 ms p95 budget is probably dominated by Python overhead, JPEG decode/crop and Windows timer jitter, not by the GEMMs. **Measure p50/p95/p99 over ≥1,000 warm calls with `time.perf_counter_ns`, after ≥50 warm-up runs, on battery and on AC (laptop GPUs throttle and change clocks).**
- Default runtime: start with **PyTorch eager FP16 plus `torch.inference_mode()`**, a single persistent model and a pre-allocated input tensor. Move to ONNX Runtime CUDA EP only if the p95 budget is missed or a torch-free runtime is wanted. TensorRT adds install friction on Windows (separate TensorRT install, per-GPU engine cache) and is likely unnecessary at 2.5 fps. DirectML is a fallback for non-NVIDIA machines, but it is in sustained engineering and is single-threaded per session.
- Packaging metadata dict in `model.pt`: `{"state_dict", "arch", "timm_name", "num_classes", "class_names", "input_size", "mean", "std", "crop_spec", "dataset_sha", "git_sha", "schema_version", "created_utc"}`. The loader asserts that `schema_version` and class names match the runtime's enums.
- Grad-CAM: keep a PyTorch copy of the same weights in the explanation worker. Golden tests should assert that the ONNX and PyTorch top-1 agree on the fixtures, so the explanation always describes the model that made the decision.

### Gaps
- **No primary measured latency for ResNet18 / ConvNeXt-T / DINOv2-S / EfficientNet-B0 at 224 px on an RTX 3050 or 4050 laptop GPU was found** (PyTorch, ORT CUDA, TRT). Run `timm/benchmark.py` and `trtexec` locally. This should be a ticketed measurement.
- DINOv2-S/14 at 224 px gives 256 patch tokens, so it is heavier than ResNet18. No laptop numbers were found.

---

## 5. Runtime architecture for real-time HITL

### Takeaway
Use **one deterministic action-path process**: capture -> crop -> cause model -> conformal -> gate -> (OctoPrint command), with a fixed order, no network calls and a bounded queue. Push **heavy, non-safety work** (Grad-CAM, embedding/drift stats, thumbnails) onto a separate worker (thread or `multiprocessing` process) via a bounded `queue.Queue` that drops when full. Persist everything to **SQLite in WAL mode** with one writer and many readers. The **Streamlit dashboard reads SQLite read-only and polls with `@st.fragment(run_every="1s")`**. FastAPI plus WebSocket is unnecessary unless sub-second push is required.

### Cited Findings
- SQLite WAL: readers don't block writers and writers don't block readers, but there is still **only one writer at a time**. Set `PRAGMA busy_timeout` so a second writer waits instead of returning `SQLITE_BUSY`. Old readers can block checkpoints, and a checkpoint can block a writer. Large transactions (>tens of MB) are better off in rollback mode. WAL needs all processes on the same host (no network shares). The setting persists in the DB file — [sqlite.org WAL](https://www.sqlite.org/wal.html); [Kunal Ganglani: SQLite WAL limits](https://www.kunalganglani.com/blog/sqlite-production-api-wal)
- Streamlit `st.fragment(run_every=...)` reruns only the fragment on a timer. `run_every=None` stops auto-reruns. Reruns run sequentially. Very short intervals (~33 ms) can freeze the frontend. Before 1.37 the API was `st.experimental_fragment` — [Streamlit st.fragment API](https://docs.streamlit.io/develop/api-reference/execution-flow/st.fragment); [Start/stop fragment auto-reruns tutorial](https://docs.streamlit.io/develop/tutorials/execution-flow/start-and-stop-fragment-auto-reruns); [forum: live streams](https://discuss.streamlit.io/t/efficiently-visualizing-multiple-live-data-streams-in-streamlit/88653)
- DirectML EP sessions can't be called from multiple threads concurrently — [ORT DirectML EP](https://onnxruntime.ai/docs/execution-providers/DirectML-ExecutionProvider.html)
- "Hidden feedback loops" and "undeclared consumers" are technical-debt risks. The dashboard reading the store directly is an undeclared consumer unless the schema is versioned — [Sculley et al.](https://papers.nips.cc/paper/5656-hidden-technical-debt-in-machine-learning-systems)

### Inferences
- Determinism on the action path: the gate is pure Python with no I/O, takes (prediction set, telemetry snapshot, config) and returns (decision, reason). The action path never waits on the explanation worker. Grad-CAM results are joined to events later by `event_id`.
- At 2.5 fps (400 ms/frame), a single process with one inference thread plus one background worker has ample headroom. GPU contention between the action-path model and the Grad-CAM worker on a 4 GB card should be avoided: run CAM on the GPU only when the action path is idle, or on CPU, and rate-limit CAM (e.g. only for events that reach the gate or the operator).
- SQLite: a single writer connection owned by the loop, with `journal_mode=WAL`, `synchronous=NORMAL` and `busy_timeout=5000`. Streamlit opens `file:...?mode=ro` URIs. Batch frame-level inserts, e.g. every 1 s, to keep transactions small.
- FastAPI plus WebSocket becomes worthwhile only if operator response must appear in <1 s or several clients need push. Streamlit polling at 1-2 s fits HITL acknowledgement timescales.

### Gaps
- No measured numbers on Windows timer and scheduler jitter for Python loops were found. Measure p99 loop period.

---

## 6. Monitoring and drift in production

### Takeaway
Use **hand-rolled, cheap monitors written to SQLite** and shown in Streamlit: (a) a rolling mean/entropy of softmax and **conformal set-size** distribution vs the calibration baseline; (b) an **embedding-distance** check, e.g. mean Mahalanobis or k-NN distance of penultimate features to the training set, plus a periodic **MMD permutation test** on a window vs a reference sample; (c) **empirical conformal coverage on operator-labelled events** with a binomial CI. Retrain or re-calibrate when coverage's CI upper bound falls below the target, or when drift alarms persist across N prints. Alibi-detect's `MMDDrift` is the closest off-the-shelf fit for image embeddings. Evidently and NannyML are tabular/univariate-first and add weight.

### Cited Findings
- Alibi-detect MMD drift: for images and other high-dimensional data, reduce dimensionality first (UAE, BBSD/softmax outputs, or a pretrained embedding). It is then detecting drift in the embedding, not strictly in p(x). There is also an online MMD variant — [alibi-detect MMDDrift](https://alibi-detect.readthedocs.io/en/v0.7.2/methods/mmddrift.html); [Online MMD](https://alibi-detect.readthedocs.io/en/v0.7.0/methods/onlinemmddrift.html) (older docs versions, so check the current API)
- A 2024 comparison (D3Bench) of Evidently, NannyML and Alibi-Detect: Evidently stands out for general data-drift detection, while NannyML is better at pinpointing when a shift happens and its effect on accuracy. The study covered **univariate** tabular drift, and NannyML criticised the lack of multivariate tests — [arXiv 2404.18673](https://arxiv.org/html/2404.18673v2); [NannyML blog](https://nannyml.com/blog/data-drift-does-it-matter)
- Measuring drift in embeddings (Euclidean/cosine distance to a reference, model-based detectors) — [Towards Data Science: How to measure drift in ML embeddings](https://towardsdatascience.com/how-to-measure-drift-in-ml-embeddings-ee8adfe1e55e)
- Google MLOps Level 1 retraining triggers: on-demand, scheduled, new-data availability, performance degradation, concept drift — [Google Cloud MLOps guide](https://docs.cloud.google.com/architecture/mlops-continuous-delivery-and-automation-pipelines-in-machine-learning); summary in [open-exam-prep](https://open-exam-prep.com/study-guides/gcp-machine-learning/domain-5-automating-pipelines/mlops-cicd-retraining)
- Hidden feedback loops: a model that influences its own future training data, such as operator labels collected only on flagged events, is a named debt risk — [Sculley et al.](https://papers.nips.cc/paper/5656-hidden-technical-debt-in-machine-learning-systems)

### Inferences
- Alibi-detect pulls in TensorFlow or PyTorch extras and has had slow releases. A ~40-line MMD with an RBF kernel, median-heuristic bandwidth and a permutation test in torch or numpy is easy to unit-test and avoids the dependency. Prefer it, and cite alibi-detect for the method.
- Coverage monitoring: for each operator-labelled event, record `true_label in prediction_set`. Over a rolling window of n labels, compute a Clopper-Pearson CI on coverage. Alarm if the upper bound is < 1-α. Labels are not i.i.d. (operators label flagged events more), so also log label-selection reason to make the bias visible. This is the feedback-loop risk above.
- Active learning: queue low-margin, large-set or high-embedding-distance frames for operator labelling, capped per print. Store `(event_id, crop_path, model_version, label, labeller, ts)`. These labels feed recalibration first and retraining second.
- Retraining triggers for a UG team: manual, in pre-registered checkpoints, e.g. "after K new labelled prints or a persisting coverage/drift alarm". Automatic continuous training (Google Level 1) isn't warranted. Stay at Level 0+ with scripted, reproducible pipelines.

### Gaps
- No published, laptop-scale benchmark of MMD/embedding-drift sensitivity for FFF nozzle images was found. Thresholds need calibrating on held-out prints and synthetic shifts (lighting, focus, new filament colour).
- Current alibi-detect API and version compatibility with Python 3.11 / torch 2.x were not verified.

---

## 7. Testing and CI for ML code

### Takeaway
Use **pytest markers** (`gpu`, `hw`, `slow`) excluded by default. Add a **`--limit N --epochs 1` CPU smoke run** of every script in CI, **golden-fixture artifact tests**, and **schema/contract tests** on the SQLite store and the data CSVs. CI runs on CPU-only GitHub Actions, and GPU tests run manually from runbooks.

### Cited Findings
- Google MLOps Level 2 adds CI/CD for pipeline code: building, testing and deploying pipeline components automatically — [Google Cloud MLOps guide](https://docs.cloud.google.com/architecture/mlops-continuous-delivery-and-automation-pipelines-in-machine-learning)
- ML-specific debt includes configuration debt, data dependencies and pipeline jungles, which tests on configs and data schemas address — [Sculley et al.](https://papers.nips.cc/paper/5656-hidden-technical-debt-in-machine-learning-systems)
- With deterministic algorithms enabled, PyTorch raises on known non-deterministic ops. That is useful in a CPU test that checks reproducibility of a tiny training run — [PyTorch reproducibility](https://docs.pytorch.org/docs/stable/notes/randomness.html)

### Inferences
- Useful tests: (1) a tiny-model overfit test: 16 images, 30 steps, loss falls below X, on CPU in under 10 s. (2) Seeded run twice gives identical metrics on CPU. (3) The exporter round-trips, with ONNX vs PyTorch max-abs-diff < 1e-4 FP32 on fixtures. (4) A `CauseModel.predict` signature test asserting it only accepts (crop, defect). This enforces the "no setpoints/telemetry into cause model" rule mechanically. (5) Gate property tests: no command is emitted outside `gate()`. (6) A latency test marked `gpu` asserting p95 ≤ 30 ms.
- `uv` lockfile plus `uv sync` gives reproducible envs. Pin the CUDA torch index in pyproject for the GPU laptops and the CPU wheel for CI.

### Gaps
- No source was retrieved on uv-specific CI patterns or CUDA/CPU index pinning. Check the uv docs on "PyTorch integration".

---

## Summary: recommended stack and chain (synthesised from the above)

| Stage | Recommendation | Optional upgrade |
|---|---|---|
| Data | ROI-crop + resize once; tar shards by print (WebDataset format) or `.npy` feature cache | LMDB |
| Versioning | sha256 manifest (Parquet/CSV) + `dataset_sha` in git; DATASHEET.md | DVC with a shared remote |
| Training | plain PyTorch + timm; AMP; grad-accum; frozen/partial backbone | gradient checkpointing; `torch.compile` |
| Config | YAML -> dataclass; resolved config saved into run.json | OmegaConf |
| Tracking | `runs/<id>/run.json` + `metrics.jsonl` (git SHA, data hashes, seeds, versions) | TensorBoard; MLflow with SQLite backend |
| Evaluation | LOGO grouped CV; group bootstrap CIs; pre-registered rule; golden fixtures; model card | — |
| Registry | `models/<name>/<ver>/` directory + REGISTRY.json pointer | MLflow Model Registry (SQLite) |
| Runtime | PyTorch FP16 inference_mode in one process; measure p95 | ONNX Runtime CUDA EP; TensorRT EP FP16 with engine cache; DirectML on non-NVIDIA |
| Explanation | pytorch-grad-cam on PyTorch weights in a background worker, bounded drop-queue | — |
| Store/UI | SQLite WAL (one writer, busy_timeout); Streamlit `st.fragment(run_every="1s")` read-only | FastAPI + WebSocket |
| Monitoring | entropy/set-size shift, embedding distance, hand-rolled MMD, labelled-coverage CI | alibi-detect MMDDrift; Evidently reports |
| Retraining | manual, triggered by pre-registered thresholds; recalibrate conformal first | scheduled pipeline (Google Level 1) |
| CI | pytest markers gpu/hw/slow; CPU smoke `--limit`; ruff; GitHub Actions CPU | — |
