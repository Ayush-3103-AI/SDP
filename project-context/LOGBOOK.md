# LOGBOOK (append-only; newest at the bottom)

## 2026-10-03 — Phases 0–4 (compressed) — Charter, spec, tickets
BUILT:     00-charter, 01-understanding, 02-stakeholders, 03-landscape, 04-patterns, ADR-0001..0007,
           06-requirements (25 MUST/SHOULD FRs + 3 COULD, 11 NFRs), 07-math, 08-pseudocode,
           09-interfaces, 10-done, 52 tickets + BOARD.md, root CLAUDE.md
RESULT:    Gate pending
SURPRISE:  - The model files in the repo root (AM_1/AM_2 .pt) are older YOLOv8n iterations: one has junk
             classes (defect/object/p/s); the other has a duplicated typo class "under exstrosion". They are
             NOT the deck's YOLO11-S. The 2025/26 papers' metrics don't match the shipped files either.
           - Defects were induced by commanding setpoints, so any model that sees setpoints or telemetry
             would score ~100 % on the cause — this became ADR-0002's one-way rule.
           - The deck's fixed recipes (e.g. M104 S190 from 210 = −20 °C) will violate our own L2 step
             limit; the recipe audit (T-0023) turns that into a result.
BROKE:     Nothing (no code yet)
NEXT:      Gate approval → T-0001 (Claude Code), T-0002 (human, day 1)

## 2026-10-03 — T-0001 Scaffold the repo
SKIP:      SEQUENCE step 1 (T-0002) is HUMAN-owned; skipped per rule 2. It still has to start on day 1.
BUILT:     pyproject.toml (uv + hatchling, deps per ticket, dev group pytest/ruff, markers gpu/hw/slow,
           addopts excludes them; torch/torchvision from the explicit pytorch-cu126 index), .python-version (3.11),
           uv.lock (torch 2.14.1+cu126), xqi/__init__.py (__version__ 0.1.0), tests/test_smoke.py.
           .gitignore += data/* (not data/splits/), runs/, models/* with the models/cause/{final.pt,qhat.json,
           preds_*.npz} whitelist, graphify-out/, .graphify/; graphify-out untracked.
RESULT:    `uv run pytest` → 1 passed; `uv run ruff check .` clean; check_sequence.py OK; check-ignore verified.
SURPRISE:  - T-0001 was revised mid-session (commit a8e9ad8: cu126 source + models/cause whitelist). The first
             pass built the old spec; /code-review caught both gaps and they were fixed before commit.
           - Default ruff flags `re.M` in scripts/check_sequence.py (FURB167); fixed to re.MULTILINE.
           - C: has < 1 GB free; the 2.4 GB CUDA torch wheel can't unpack into uv's default cache there.
             Synced with UV_CACHE_DIR=D:/uv-cache (per command, not persisted).
BROKE:     Nothing.
NEXT:      SEQUENCE step 3 = T-0003 (contracts module).

## 2026-10-03 — Ticket edit: /ml-model-builder gates in the cause-model tickets (user request)
BUILT:     A `Skill:` line plus gate-specific spec items in T-0006, 0007, 0009, 0010, 0011, 0012, 0013, 0015, 0017:
           Gate 0 frame (cause_model.py docstring), Gate 1 near-duplicate audit + split check, Gate 2 ladder
           (frozen-backbone linear probe vs fine-tune; fine-tune kept only if it beats the probe by > fold std),
           Gate 3 overfit-20 check + reproducibility hashes + fold-local class weights, Gate 4 ECE / slices /
           worst-error grid / staleness, Gate 5 self-describing final.pt + golden-crop artifact test.
RESULT:    check_sequence.py OK (no dependency or order change). GitHub issue bodies synced.
SURPRISE:  sklearn isn't installed, so the linear probe is the same torch model with the backbone frozen
           (no new dependency, no API change to 09's build_model()).
BROKE:     Nothing. 08-pseudocode P5 doesn't mention the probe rung yet (edit 06–09 only with approval).
NEXT:      SEQUENCE step 3 = T-0003.

## 2026-10-04 — Review of teammate's P1 (T-0003, T-0004, T-0032; PRs #53–#55)
BUILT:     Review only, plus two fixes. xqi/store.py: SCHEMA_VERSION is now imported from xqi.types (the
           duplicate copy would have silently diverged on a bump, which breaks the Versioning rule);
           write_detection(obj, ts) now stores the frame's ts (before, every detections.ts was hard-coded 0.0).
           tests: test_detection_keeps_frame_ts; test_causes_yaml_matches_type_defaults (causes.yaml vs types.py).
           BOARD rows for T-0003/0004/0032 → DONE (the PRs closed the issues but left BOARD/STATE/LOGBOOK alone).
RESULT:    Each Done-when checked against 09-interfaces: every type round-trips through JSON; default.yaml loads
           and all 6 validation rules raise ConfigError naming the key; store round-trips every table with WAL and
           the two-process decision insert works. `uv run pytest` → 40 passed; ruff clean.
SURPRISE:  - Nothing reads config/causes.yaml at runtime yet. 09 §Module APIs only lists config.load(), so no loader
             was added (that would be an API change). The drift test keeps it equal to the types.py defaults until
             T-0007 edits it, and at that point a loader has to exist (DESCEND to add it to 09).
           - Store detections are batched every 25 detections, not every 25 frames. That's harmless at this scale.
           - Store.query()'s read-only check is a prefix match ("WITH … DELETE" would get through on the loop
             connection). The UI side is safe because open_readonly uses mode=ro.
BROKE:     Store.write_detection signature (ts now required). No callers yet.
NEXT:      SEQUENCE step 6 = T-0021 (gate L1+L2). T-0002 (HUMAN) is still open.

## 2026-10-04 — DESCEND (user-approved): load_causes() + the remaining P1 review fixes
BUILT:     09-interfaces §Module APIs: added `load_causes(path) -> Causes`. This is the DESCEND, approved by the
           user ("fix the issues"). xqi/config.py: frozen Causes dataclass and load_causes(), which validate that
           every cause_action/cause_defects key is in causes, each var is in Var, each direction is ±1, and every
           defect is in DEFECTS. A violation raises ConfigError naming the key. xqi/store.py: detections are now
           flushed every 25 distinct frames (the spec says frames, not detections); query() runs under
           PRAGMA query_only, so "WITH … DELETE" can no longer write.
RESULT:    `uv run pytest` → 45 passed (+5: 3 load_causes rejections, CTE write rejected, frame batching); ruff clean.
           No SCHEMA_VERSION bump: the change is additive config API, not §Types/§Store/§Data.
SURPRISE:  Nothing.
BROKE:     Nothing.
NEXT:      SEQUENCE step 6 = T-0021 (gate L1+L2). T-0002 (HUMAN) is still open.

## 2026-10-26 — T-0014: Implement split-conformal calibration and prediction sets (parallel run)
BUILT:     xqi/explain/conformal.py: calibrate (LAC score 1−p_y, np.quantile method=higher at ⌈(n+1)(1−α)⌉/n;
           level > 1 gives 1.0; n < 20 raises ValueError), predict_set (label order, inclusive ties),
           save_qhat/load_qhat as JSON {qhat, alpha, n}. Added an empty xqi/explain/__init__.py so the package
           exists. tests/test_conformal.py covers coverage, n < 20, level > 1, ties and the save/load roundtrip.
RESULT:    Dirichlet-calibrated categorical model, K=5, n_cal=5000, 20 000 test draws: coverage 0.9535 at α=0.05,
           0.9085 at α=0.1, 0.80445 at α=0.2, all inside [1−α−0.01, 1−α+0.03]. Merged t0014 into main with
           --no-ff, no conflicts. `pytest -q` → 52 passed; ruff clean on the tracked tree.
SURPRISE:  - Checking p ≥ 1−qhat directly can drop an exact tie by one ulp, because 1−(1−p) ≠ p in floats.
             predict_set compares the score 1−p ≤ qhat instead, the same expression calibrate uses, so ties are
             included exactly.
           - 09-interfaces doesn't fix what load_qhat returns. It returns {"qhat", "alpha", "n"} because CauseSet
             needs both alpha and qhat.
           - `ruff check .` from the repo root also lints the untracked agent worktrees under .claude/worktrees/
             (there, isort doesn't treat xqi as first-party). With --extend-exclude .claude it's clean.
BROKE:     Nothing.
NEXT:      The Explainer fills CauseSet(alpha, qhat) from load_qhat. scripts/eval_conformal.py (empirical coverage on
           LOGO folds) waits on real cause-model probs.

## 2026-10-26 — T-0016: Implement proposal and counterfactual generation (severity-scaled Δ, G-code, sentence) (parallel run)
BUILT:     xqi/explain/counterfactual.py: severity() per 07 §1; make_proposal() per §2 (severity-scaled Δ from
           cfg.correction d_min/d_max, integer G-code, counterfactual sentence with S+W = verify.settle_s +
           window_s = 150 s); recipe_to_proposals() (deck recipe minus the current setpoint, one Proposal per
           variable); the shared round_half_up() and gcode() helpers. tests/test_counterfactual.py has the
           table-driven tests.
RESULT:    flow_low s=0 → +5, s=1 → +10 → `M221 S110` from 100. nozzle_temp_high s=0.5 from 210 → 206.5 →
           `M104 S207` (math.floor(x+0.5)). none and misalignment → None. under_extrusion recipe from nominal →
           3 proposals: nozzle −5, speed −20, flow +10. Merged t0016 into main with --no-ff, no conflicts.
           `pytest -q` → 73 passed (21 new); ruff clean on the tracked tree (--extend-exclude .claude).
SURPRISE:  - The 09 signature make_proposal(cause, p, severity, state, cfg) has no defect_id, but Proposal needs one.
             Added an optional keyword defect_id='' so the 09 call still works. Proposal ids are deterministic:
             '<defect_id>-<cause>' and '<defect_id>-recipe-<var>'. Recipe proposals use cause='recipe'.
           - Cause label = cause.replace('_',' '); the flow/speed unit is '%'. The spec defines neither.
           - severity(area_frac, recent_hits, cfg) takes the full Config (reads cfg.severity.a_ref, matching the 07 §1
             notation). ConfirmationTracker holds only severity_cfg, so it needs the full cfg or a small wrapper.
           - The branch had no xqi/explain/__init__.py; main already has one from T-0014, so it's a regular package.
BROKE:     Nothing.
NEXT:      Gate (T-0021 etc.) imports round_half_up/gcode from xqi.explain.counterfactual so G-code rounding stays
           in one helper. The Explainer passes defect_id=cd.defect_id. The recipe speed Δ −20 exceeds the L2 step
           of 10, so the gate clips it, as gated-recipe mode intends.

## 2026-10-26 — T-0019: Implement the telemetry sensor checks (parallel run)
BUILT:     xqi/explain/sensors.py: check(history, now, cfg), a pure function per 07 §5. It flags
           heater_deviation:nozzle|bed when the continuous run of |act-tgt| > cfg.sensors.temp_dev_c, ending at the
           latest sample, has lasted more than temp_dev_s. It flags settling:<v> for each v in cfg.sensors.settle_s
           whose target changed less than settle_s ago (the latest of last_change_ts[v] and any target step seen in
           the history). It flags printer_not_printing when the state is not "Printing". Empty history returns
           ("state_unavailable",). tests/test_sensors.py has the table-driven tests.
RESULT:    A 6 °C deviation for 12 s → heater_deviation:nozzle; for 8 s → (); exactly 5 °C → no flag (strict >).
           A nozzle target changed 30 s ago → settling:nozzle_temp (from both the history and last_change_ts). A bed
           change 60 s ago still settles while the nozzle (45 s) does not. Empty history → ("state_unavailable",).
           Merged t0019 into main with --no-ff, no conflicts. `pytest -q` → 84 passed (11 new); ruff clean on the
           tracked tree (--extend-exclude .claude).
SURPRISE:  - A target change comes from both last_change_ts (our own commands) and history diffs (slicer-issued
             M104/M140), so a G-code target change also counts as settling.
           - The deviation duration is measured from the first deviating sample still in the history. If the window
             is shorter than temp_dev_s, the flag can fire late, never early (conservative for APPLY blocking).
           - The branch added an empty xqi/explain/__init__.py; main already had an identical one, so the merge
             didn't touch it.
BROKE:     Nothing.
NEXT:      The Explainer and event_verdict/L4 consume these flags: any flag blocks APPLY, and state_unavailable maps
           to ESCALATE per §4 row 4.

## 2026-10-26 — T-0026: Implement the Printer protocol and the FakePrinter simulator (parallel run)
BUILT:     New xqi/printer.py has a runtime_checkable Printer Protocol (get_state, send_gcode, pause, resume, estop)
           and FakePrinter(clock=time.monotonic, nozzle_c=210, bed_c=60). FakePrinter parses the S value of
           M104/M140/M220/M221, handles M112, keeps a `sent` list of (ts, line), tracks last_change_ts for each Var,
           and runs a Printing/Paused/Error state machine. Thermal lag follows 07 §12 (tau 8 s nozzle, 60 s bed)
           using explicit Euler in sub-steps of at most 0.1 s. Flow and speed change instantly.
RESULT:    M104 S220 from 210 gives nozzle 216.34 after 8 s (expected 216.32, tolerance ±0.5). M221 S110 sets
           flow_pct to 110 at once. After M112 the state is Error and send_gcode returns False. Also tested: the bed
           tau, the `sent` contents, and pause/resume. Merged t0026 into main with --no-ff, no conflicts.
           `pytest -q` → 88 passed (4 new); ruff clean on the tracked tree (--extend-exclude .claude).
SURPRISE:  - Taken literally, "Euler at the call rate" with a single 8 s step gives dt/tau = 1, so the nozzle jumps
             straight to 220 and the Done-when test fails; gaps longer than 2*tau would oscillate. Fixed by
             splitting each gap into Euler sub-steps of at most 0.1 s, which still matches the closed form.
           - last_change_ts starts at -inf ("never changed"), so the L2 cooldown does not block corrections at t=0
             when the fake clock starts there.
           - Unspecified but inside the 09 API: initial temps come from constructor kwargs (defaults 210/60, the
             config nominal); progress_pct is None; pause/resume are not written to `sent` (G-code only); estop()
             returns True once the printer is in Error.
BROKE:     Nothing.
NEXT:      OctoPrintClient (the real Printer, with mocked HTTP) and the gate/loop tickets can use FakePrinter as
           their printer double.

## 2026-10-26 — T-0021: Implement safety gate layers L2 (rate/cooldown) and L1 (physical limits) (parallel run)
BUILT:     New xqi/gate.py has gate(p, state, now, cfg) -> GateDecision, a pure function (07 §3, P4). Order:
           fail-closed state check -> L2 (cooldown reject, then clip |delta| to step) -> round_half_up -> L1
           (physical limits) -> L3 stub (always passes). It also holds round_half_up(x) = floor(x + 0.5) and the
           integer G-code map for M104/M140/M221/M220. Every LayerResult carries a readable reason, e.g.
           'L2: clipped +15 → +5 °C', 'L2: cooldown 10s < 45s', 'L1: 245 °C outside [170, 240]'. The gate reads only
           cfg.envelope.L1 and cfg.envelope.L2.
RESULT:    Table tests pass: clip +15 -> +5 °C (flow +15 -> +10 gives M221 S110), cooldown reject at 10 s < 45 s,
           physical reject at 245 °C, rounding 240.5 -> 241 -> L1 reject, and state None / NaN setpoint / NaN
           last_change / NaN delta -> passed=False with reason 'state_unavailable'. On reject, final_delta = 0.0,
           final_value = current setpoint, final_gcode = (). Merged t0021 into main with --no-ff, no conflicts.
           `pytest -q` → 98 passed (10 new in tests/test_gate.py); ruff clean on the tracked tree (--extend-exclude .claude).
SURPRISE:  - No shared round-half-up helper existed yet. T-0016 says the gate must use the same helper, so it now
             lives in xqi/gate.py as round_half_up.
           - GateDecision has no top-level reason field, so 'state_unavailable' goes into a single LayerResult tagged L1.
BROKE:     Nothing. Only new files were added.
NEXT:      T-0022 (L3 window + event_verdict / L4) replaces the L3 stub. T-0016's counterfactual.py should import
           round_half_up (and GCODE if needed) from xqi.gate, not define its own. T-0023 property tests should allow
           |final_delta| <= step + 0.5 for non-integer setpoints (rounding).

## 2026-10-26 — T-0035: Implement the outcome verifier (parallel run)
BUILT:     xqi/verify.py has Verifier(window_s, settle_s) with a per-class (DEFECTS) deque ring buffer of
           (ts, present), pruned to the last S+2W seconds. watch(action_id, defect_id, cls, t_a) fixes r_before
           over [t_a-W, t_a]. tick(frame_ts, present) -> list[Outcome] classifies a watch once ts >= t_a+S+W.
           close() returns the remaining watches as unknown. Matches the 09 interface; the orchestrator writes
           the Outcomes to the store.
RESULT:    tests/test_verify.py at a synthetic 10 fps, W=120, S=30: 50% -> 0% gives resolved, 20% -> 40% worsened,
           30% -> 25% persisted, a run that ends early (close) unknown, and fewer than 10 before-frames unknown.
           Merged t0035 into main with --no-ff, no conflicts. `pytest -q` -> 103 passed (5 new in
           tests/test_verify.py); ruff clean on the tracked tree (--extend-exclude .claude).
SURPRISE:  The ticket test asks for 25 %, which a 10-frame on/off pattern cannot produce exactly. The test uses an
           even floor-based spreading pattern instead, so every rate is exact over the window. Windows are closed
           intervals [t0, t1]; a frame at exactly t_a+S+W is in the after window. r_before/r_after are 0.0 when a
           window has no frames, and the verdict is then unknown. A watch on a class not in DEFECTS raises KeyError.
BROKE:     Nothing. Only new files were added.
NEXT:      The orchestrator (P3/P1) calls watch() after an applied action, tick() on every frame and close() at run
           end, and passes each Outcome to store.write_outcome.

## 2026-10-26 — T-0030: Implement the YOLO11 detector wrapper (parallel run)
BUILT:     xqi/detect.py has Detector(weights, imgsz, conf, device, model=None). It wraps ultralytics.YOLO and
           imports it lazily, so it is only loaded when no model is injected. It passes imgsz, conf and device to
           predict and also re-applies the conf filter. normalise() lower-cases names, turns spaces and hyphens
           into _, strips dots, then applies ALIASES (over_extr -> over_extrusion, under_extr -> under_extrusion).
           NO_DEFECT names are dropped, and an unknown name raises ValueError at init. area_frac = box area /
           frame area. tests/test_detect.py uses a stub model and a fake Results object. The runbook is
           docs/gpu-runs/T-0030.md.
RESULT:    Fake-model tests: class mapping ('Over-extr.' -> over_extrusion, 'Layer Shift' -> layer_shift,
           'no defect' dropped), conf filter (0.1 dropped, 0.25 kept), area_frac and xyxy, empty result, and
           unknown name -> ValueError at init. The gpu test (best.pt, 1 frame at 1920x1056, < 60 ms after 3
           warm-up frames) is written and deselected by default. Merged t0030 into main with --no-ff, no
           conflicts. `pytest -q` -> 108 passed, 1 deselected (gpu); ruff clean on the tracked tree
           (--extend-exclude .claude). Status WAITING-GPU.
SURPRISE:  The real class names in best.pt are unknown until T-0002 delivers the weights. ALIASES and NO_DEFECT
           are guesses from the ticket's example. Runbook step 2 prints model.names so we can check them.
BROKE:     Nothing. Only new files were added.
NEXT:      GPU batch G1 (with T-0008), once T-0002 delivers models/yolo/best.pt: run docs/gpu-runs/T-0030.md and
           close #30 if step 3 passes. If a class name doesn't map, add an alias in xqi/detect.py.
           ConfirmationTracker (also in xqi/detect.py per 09) belongs to its own ticket.

## 2026-10-26 — T-0029: Implement the frame sources (camera and replay folder) (parallel run)
BUILT:     xqi/camera.py has open_source(spec, width, height) -> Iterator[Frame]. A spec of "<int>" opens
           cv2.VideoCapture, sets the width and height, and skips frames whose read fails. "replay:<dir>" reads
           the image files sorted by filename and skips non-images and files that cannot be read.
           "replay:<dir>@<fps>" paces playback to that fps. frame_id counts up from 0, ts comes from
           time.monotonic(), and wall_iso is a local ISO timestamp. Any other spec raises ValueError. New
           tests/test_camera.py.
RESULT:    4 camera tests: 3 run by default and 1 marked hw (deselected). The Done-when replay test passes: 3 PNGs
           written in the order b, a, c come back as 3 frames in name order (a, b, c), with frame_id 0..2,
           strictly increasing ts and BGR uint8 images, then StopIteration. Camera mode is covered by
           @pytest.mark.hw test_camera_yields_frames. Merged t0029 into main with --no-ff, no conflicts.
           `pytest -q` -> 111 passed, 2 deselected; ruff clean on the tracked tree (--extend-exclude .claude).
SURPRISE:  On Windows with Python 3.11, time.monotonic() is GetTickCount64 and ticks only every 15.6 ms, so a fast
           replay could give several frames the same ts (FR-002 needs ts to increase). ts is now
           max(monotonic(), last + 1e-6). fps pacing sleeps against perf_counter; with monotonic it failed about
           3 runs in 8. The test allows one tick of tolerance at 10 fps.
BROKE:     Nothing. Only new files were added.
NEXT:      Run `uv run pytest -m hw tests/test_camera.py` on the rig laptop with the webcam. The orchestrator
           (T-0030+) uses open_source(cfg.camera.source, cfg.camera.width, cfg.camera.height). A dead camera
           yields no frames, so the loop's max_gap_s check has to run on a timer outside the frame iterator.

## 2026-10-26 — T-0011: Implement the cause model (architecture, predict, training step) (parallel run)
BUILT:     xqi/explain/cause_model.py. The module docstring opens with the Gate 0 frame.
           build_model(n_causes, n_defects, pretrained=True) is ResNet18 (IMAGENET1K_V1) with fc=Identity; the
           512-d features are concatenated with the defect one-hot, then Linear -> n_causes.
           train_one_epoch(model, loader, opt, class_weights) runs class-weighted CE over (image, defect_idx,
           cause_idx) batches and returns (mean_loss, train_acc). CauseModel(weights, causes, defects, device,
           input_px=224).predict(crop_bgr, defect) converts BGR to RGB, resizes to 224 with INTER_AREA, applies
           ImageNet normalisation, softmaxes and returns CauseEstimate. New tests/test_cause_model.py.
RESULT:    3 new tests, written first and seen failing (ModuleNotFoundError). Probs sum to 1 over all 9 CAUSES
           and top/p_top match. inspect.signature(model.predict) is exactly ['crop_bgr', 'defect']. Done-when:
           64 synthetic red/blue "causes", random-init ResNet18, AdamW lr 3e-4, batch 16, 5 CPU epochs reach
           train accuracy > 0.9. Merged t0011 into main with --no-ff, no conflicts (xqi/explain/__init__.py
           already existed on main). `pytest -q` -> 114 passed, 2 deselected; ruff clean on the tracked tree
           (--extend-exclude .claude).
SURPRISE:  Under parallel-agent CPU load, importing torch/torchvision costs about 60 s, and the overfit test took
           about 24 s at both 64 px and 32 px, so contention dominates, not image size. Test images are 32 px
           because the backbone is size-agnostic (adaptive pool). Production predict still uses 224.
BROKE:     Nothing. Additive only: build_model gained an optional pretrained kwarg (default True, which matches
           09) so tests and CauseModel loading never download ImageNet weights. CauseModel.__init__ takes an
           optional input_px=224 so it can be wired from cfg.cause_model.input_px.
NEXT:      T-0012 (LOGO training script) reuses build_model and train_one_epoch, with aug, early stop and fold
           saving per 08 P5. The real training needs a GPU plus T-0005/6/7 data and gets a runbook then.

## 2026-10-26 — T-0022: Implement gate layer L3 and the event-verdict truth table (with L4) (parallel run)
BUILT:     xqi/gate.py: replaced the L3 stub with the 07 §3 toward-window rule (l3_pass: inside W3 or the distance
           strictly decreases; reasons 'within'/'toward'/'moves away from'). Added event_verdict(mode, cd, cset,
           est, flags, decisions, state, cfg), which implements the 07 §4 rows in order. L4 (|C|=1, C!={none},
           p_top>=tau, no flags) is evaluated inside it via _l4_fail, which returns the failure reason for row-10
           PROPOSE cards. tests/test_gate.py: L3 cases plus a parametrised test_event_verdict_table.
RESULT:    test_event_verdict_table has 19 parametrised cases covering all 10 rows, with extra cases for rows 3,
           4, 5, 8 and 10. L3: through gate(), 235 -> 230 passes although the window max is 225 (G-code M104
           S230); l3_pass(220, 230) rejects; through gate(), 225 -> 230 rejects with 'L3: 230 °C moves away from
           [195, 225]'; equal distance is not a decrease. Merged t0022 into main with --no-ff, no conflicts.
           `pytest -q` -> 136 passed, 2 deselected; ruff clean on the tracked tree (--extend-exclude .claude).
SURPRISE:  The ticket's '220 -> 230 rejects' case can't happen through gate(), because L2 clips +10 to +5 and 225
           is inside the window. So that case tests the pure l3_pass helper, and the gate-level rejection uses
           225 -> 230. cfg.critical is a dataclass (CriticalConfig), not a mapping, so row 1 uses
           getattr(cfg.critical, cd.cls, None). Spec readings (not conflicts): cset=None counts as C=∅ and gives
           ESCALATE(no_confident_cause), which fails closed; row 4 fires when state is None or any of the four
           setpoints is NaN; est=None fails L4 and gives PROPOSE; the advisory row-10 reason is the mode name,
           and the auto row-10 reason is the L4 failure reason or 'N surviving proposals'.
BROKE:     Nothing. The existing L1/L2 tests still pass, and only the stub L3 reason changed.
NEXT:      The orchestrator ticket calls gate() for each proposal (or each recipe proposal in gated-recipe mode)
           and passes the decisions to event_verdict. Rows 1 and 2 return proposal_ids=() with the configured
           action ('estop'/'pause') or 'deck_recipe' as the reason, so the caller dispatches estop/pause or the
           raw recipe itself.

## 2026-10-26 — T-0037: Build the dashboard live view (read-only) (parallel run)
BUILT:     xqi/ui_data.py holds all of the UI's SQL as pure functions over a Store: resolve_run (an id, or 'latest'
           = the newest runs/*/events.sqlite), latest_state, run_mode, last_events (a UNION over defects, verdicts,
           actions and alerts, newest first, n=50 by default) and recent_alerts (alerts within 30 s of the latest
           telemetry, both on the loop's clock). It also holds save_latest_frame, the loop-side writer: downscale
           to 640 px wide, draw red boxes, write a temp file and swap it in with os.replace. xqi/ui.py is Streamlit
           layout only (red st.error banner per alert, frame, mode/printer metrics, last-50 events table) inside
           st.fragment(run_every=0.5); read-only. launch(run) wraps `streamlit run xqi/ui.py -- --run R`.
           Runbook: docs/gpu-runs/T-0037.md.
RESULT:    tests/test_ui_data.py: 7/7 on a fixture DB (latest state, mode, empty DB, last-N events capped at 50
           newest first, alerts newest first with old ones dropped, resolve_run latest/id/missing, latest.jpg
           writer). An in-process streamlit AppTest renders ui.py and asserts the red banner, Mode=advisory,
           Printer=Printing, a 50-row table and the image. Merged t0037 into main with --no-ff, no conflicts.
           `pytest -q` -> 143 passed, 2 deselected; ruff clean on the tracked tree (--extend-exclude .claude).
           Done-when part 2 (manual check on a replay run + reports/img/ui_live.png) is WAITING-GPU.
SURPRISE:  The Spec says to add the latest.jpg write to the orchestrator 'in this ticket' and lists
           `python -m xqi ui`, but xqi/orchestrator.py and xqi/__main__.py are created by T-0033, which is not in
           Depends on. Neither file was created (avoids add/add conflicts with T-0033). Detections are buffered in
           the store 25 frames at a time, so the UI can't draw boxes from the DB in time; the loop draws them into
           latest.jpg instead. First AppTest run takes 5-16 s (streamlit init), later ones 0.05 s.
BROKE:     Nothing. On Windows os.replace can fail while the UI holds latest.jpg open; save_latest_frame then
           returns None and the next 0.5 s save retries, so the loop never crashes on the UI.
NEXT:      When T-0033 merges: (1) Orchestrator.run calls ui_data.save_latest_frame(run_path, frame.image, dets)
           at most every 0.5 s; (2) __main__ `ui --run R` dispatches to xqi.ui.launch(R). Then the team laptop runs
           docs/gpu-runs/T-0037.md (replay run + screenshot to reports/img/ui_live.png) with T-0038.
