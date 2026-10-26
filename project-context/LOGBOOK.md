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

## 2026-10-26 — T-0031: Implement the confirmation tracker (with severity) (parallel run)
BUILT:     ConfirmationTracker in xqi/detect.py, following 08 P2 line by line: per-class streak, first_ts, armed,
           absent and a recent deque(maxlen=severity.window). Each ConfirmedDefect gets a uuid4 defect_id,
           t0 = ts of the streak's first frame, t_conf = time.monotonic() (same clock as Frame.ts), severity from
           the existing counterfactual.severity(), and critical = cls in the critical set. hits < 1 raises
           ValueError. Tests in tests/test_confirm.py.
RESULT:    tests/test_confirm.py 5/5: TTT fires once at frame 3; TFTT gives no event; no re-fire after a 4-frame
           gap with rearm=5, re-fire at frame 11 after 5 misses; clog (hits=2, critical) and stringing (hits=3)
           confirm in parallel; several boxes of one class -> the max-conf box supplies conf and area_frac.
           Merged t0031 into main with --no-ff, no conflicts. `pytest -q` -> 148 passed, 2 deselected; ruff clean
           on the tracked tree (--extend-exclude .claude). Done-when met.
SURPRISE:  The 09 signature __init__(hits, rearm_frames, severity_cfg) can't receive cfg.critical, and
           CriticalConfig is a slotted dataclass, so `cls in cfg.critical` wouldn't work on it anyway. Added an
           optional kwarg critical=CRITICAL (defaults to CriticalConfig's field names: clog, layer_shift,
           spaghetti); the 09 signature still holds. severity() takes the root cfg, so the tracker wraps
           severity_cfg in SimpleNamespace(severity=...).
BROKE:     Nothing. data/raw/reu_code does not exist, so the REU confirmation counts were not ported and
           confirm.hits in config/default.yaml is unchanged.
NEXT:      T-0034 orchestrator: ConfirmationTracker(cfg.confirm.hits, cfg.confirm.rearm_frames, cfg.severity).
           08 P3's `cd.cls in cfg.critical` should use cd.critical, plus getattr(cfg.critical, cd.cls) for the
           estop/pause action (CriticalConfig is not a dict). Optional 09 note:
           `ConfirmationTracker.__init__(hits, rearm_frames, severity_cfg, critical=CRITICAL)`. Once T-0002
           delivers data/raw/reu_code, port its hit counts into confirm.hits.

## 2026-10-26 — T-0027: Implement the OctoPrint REST client (parallel run)
BUILT:     OctoPrintClient(cfg, clock) in xqi/printer.py. requests.Session with the X-Api-Key header from
           os.environ[cfg.printer.api_key_env]. GET /api/printer (temps, state), GET /api/job (progress),
           POST /api/printer/command (G-code), POST /api/job pause/resume; estop sends M112. Every request uses
           timeout=cfg.printer.timeout_s with one retry. flow/speed start at cfg.printer.nominal and change only
           after a successful M221/M220 send; last_change_ts tracked locally for every var. M104/M140/M220/M221
           parsing moved out of FakePrinter into a shared _setpoint() helper so both printers parse G-code alike.
RESULT:    tests/test_octoprint.py 10/10 with Session.request monkeypatched (no real network): state parsed from
           a recorded /api/printer JSON + progress from /api/job; send_gcode posts exactly {"commands": [...]}
           and tracks setpoints; timeout on both tries -> False, flow_pct/last_change_ts unchanged; connection
           error retried once; pause/resume/estop bodies; key never in caplog text or repr (even when an
           exception message contains it); missing env var -> KeyError naming the var.
           Merged t0027 into main with --no-ff, no conflicts. `pytest -q` -> 158 passed, 2 deselected; ruff clean
           on the tracked tree (--extend-exclude .claude). Done-when met.
SURPRISE:  08 P3 says retry on non-2xx or timeout; the ticket only says connection error. The client retries
           once on any RequestException or non-2xx (the broader P3 rule). M220/M221/M104/M140 S-values are
           absolute, so the retry is idempotent. The orchestrator must NOT add its own retry (would make up to
           4 attempts per send).
BROKE:     Nothing. FakePrinter behaviour unchanged after the _setpoint refactor (test_printer_fake green).
NEXT:      Orchestrator: wrap get_state in try/except OSError -> state=None so P3 row 4 escalates (get_state raises
           OSError when /api/printer fails after its retry; a failed /api/job only sets progress_pct=None). The
           __main__/orchestrator factory picks OctoPrintClient vs FakePrinter from cfg.printer.kind. Real-printer
           (hw marker) checks not run, per the no-hardware rule.

## 2026-10-26 — T-0020: Assemble the Explainer (cause model → conformal set → sensor flags → proposals) (parallel run)
BUILT:     xqi/explain/__init__.py: crop(image, xyxy, pad) pads the pixel box by pad x its width/height and clips
           it to the image. Explainer(cause_model, qhat, labels, cfg).explain(cd, frame, history) runs
           cause_model.predict(crop, cd.cls), then conformal.predict_set, then a CauseSet(alpha=cfg.conformal.alpha,
           qhat), then sensors.check(history, now=cd.t_conf), then make_proposal for each actionable member in
           descending probability order. It does no gating. tests/test_explain.py uses a stub cause model.
RESULT:    5 new tests in tests/test_explain.py. probs {flow_low .6, nozzle_temp_low .3, none .1} with qhat .8 ->
           2-member set and 2 proposals ordered [flow_low, nozzle_temp_low]; {none}-only set -> 0 proposals;
           misalignment in the set is skipped; empty history -> ('state_unavailable',) and no proposals; crop
           shape checks pass. Merged t0020 into main with --no-ff, no conflicts. `pytest -q` -> 163 passed,
           2 deselected; ruff clean on the tracked tree (--extend-exclude .claude). Done-when met.
SURPRISE:  The spec does not say which state make_proposal should use or which 'now' sensors.check should use.
           Chosen: the latest state in history by ts, and cd.t_conf (monotonic, the same clock as
           PrinterState.ts) so explain stays pure. With empty history it returns [] proposals and the
           gate/event_verdict handles state=None. xyxy is in pixel coordinates, as Detector produces it; the
           cause model's probs are read in `labels` order to build the predict_set input.
BROKE:     Nothing. xqi/explain/__init__.py imports only conformal, sensors and counterfactual, so it does not
           pull in torch.
NEXT:      Orchestrator (P3 handle_event) wires Explainer and gate together: build CauseModel and
           load_qhat(cfg.conformal.qhat_file) at startup and pass them to Explainer.

## 2026-10-26 — T-0023: Write the randomised gate property test and the deck-recipe audit (parallel run)
BUILT:     tests/test_gate_property.py is a seed-0 random property test with no hypothesis library. It runs
           sequential dispatch in 10-proposal episodes. Start states are integer setpoints in the L1 box ±20 %
           with random last-change times, and Δ ~ U[−50, 50]. Every dispatched change is checked against the
           07 §3 invariant (step, L1, L3 window-or-closer, cooldown since the previous dispatch). The checker is
           written from config and does not use gate.py. A 1 000-case test runs by default; a 100 000-case @slow
           test writes reports/gate_property.md. scripts/gate_audit.py pushes each DECK_RECIPE from nominal
           through gate() and writes reports/recipe_audit.md (committed). Runbook: docs/gpu-runs/T-0023.md.
RESULT:    The 1 000-case run had 0 violations. Every layer (L1, L2, L3) both blocked and passed cases, so the test
           is not vacuous. The checker unit test shows it flags step, L1, L3 and cooldown breaches. recipe_audit.md:
           5 of 10 fixed recipe changes violate the envelope as written (over_extrusion nozzle/flow and stringing
           nozzle break step+L3; under_extrusion speed and stringing speed break step). The gate clips all 5 at
           L2. Merged t0023 into main with --no-ff, no conflicts. `pytest -q` -> 166 passed, 3 deselected; ruff
           clean on the tracked tree (--extend-exclude .claude). Done-when still open: the 100 000-case slow run
           is on the team laptop (CPU only, < 2 min).
SURPRISE:  The gate rounds after the L2 clip, so a fractional setpoint can overshoot the step: 210.5 + 5 gives
           M104 S216, a dispatched Δ of 5.5 > step 5. The property test samples integer setpoints, which is
           realistic because Marlin stores targets and percentages as integers and the gate sends only integer
           G-code. The report states this scope limit. Fractional states would break the invariant.
BROKE:     Nothing. No shared files and no xqi/ code were touched.
NEXT:      The team runs docs/gpu-runs/T-0023.md (`uv run pytest -m slow tests/test_gate_property.py`) and pushes
           reports/gate_property.md showing 0 / 100000, then T-0023 closes. Separately, decide whether gate.py
           should clamp |round(x+Δ')−x| ≤ step for fractional setpoints (a small T-0022 follow-up: after
           round_half_up, step x2 back by 1 toward x when |x2 − x| > step).

## 2026-10-26 — T-0033: Implement the orchestrator: baseline mode, critical-first handling, timings, CLI (parallel run)
BUILT:     xqi/orchestrator.py has Orchestrator.run (the P1 loop) and handle_event (the critical and baseline
           branches of P3), plus git_sha() ('nogit' if git fails) and new_run_id() (UTC stamp like
           20261026T101500Z). xqi/__main__.py adds `run --config --mode --max-frames` (`--mode` overrides cfg.mode
           via dataclasses.replace; printer.kind 'fake' gives a FakePrinter) and `ui --run R` (calls
           xqi.ui.launch). tests/test_orchestrator.py has 8 tests.
RESULT:    test_baseline_parity runs replay PNGs through open_source, a stub detector and a FakePrinter end to end
           in about 0.2 s (< 10 s Done-when); an under_extrusion event sends exactly M104 S205, M220 S80, M221 S110.
           test_critical_first: the printer has already received ['M112'] with 0 explanation rows when the stub
           explainer is called, and action.t_disp < explanation.t_cause (FR-005). test_timings_logged: t0 <= t_conf
           <= t_disp. Also covered: camera gap pauses + alert; 10 detector failures in a row pause, alert and raise;
           --max-frames; the CLI override writes mode=baseline into the runs row. Merged t0033 into main with
           --no-ff, no conflicts. `pytest -q` -> 174 passed, 3 deselected; ruff clean on the tracked tree
           (--extend-exclude .claude).
SURPRISE:  T-0037's runbook expects T-0033 to add the dashboard hook (save_latest_frame every 0.5 s) and the `ui`
           dispatch, so both are here. The UI reads telemetry, so the loop polls get_state every printer.poll_s,
           writes telemetry rows and keeps a 300-entry history that explain() needs. Risk for T-0036: the frame
           source blocks, so the first YOLO call's CUDA warm-up counts as camera time; warm-up > max_gap_s (3 s)
           can trigger a false camera_gap pause on the second frame.
BROKE:     Nothing. In gated-recipe, auto and advisory modes a non-critical defect writes only its defect and
           timing rows and sends nothing (T-0034 fills that branch). The CLI passes explainer=None for now.
NEXT:      T-0034: gated-recipe, auto and advisory paths; move the critical explain_only call onto the worker
           queue (synchronous for now, ponytail comment); wire the real Explainer into __main__. Operator-decision
           processing and check_timeouts (FR-019) are also still open.

## 2026-10-26 — Parallel run 1 (24 unblocked CODE tickets, user-requested) + camera-roll audit
BUILT:     The user asked for a parallel agent setup with no heavy compute on this laptop. A workflow built each
           unblocked CODE ticket in its own git worktree, test-first, in dependency order. One serial integrator
           merged each ticket into main, re-ran the suite and ruff, updated BOARD/LOGBOOK and pushed.
           This overrides "one ticket per session" at the user's request. SEQUENCE order is unchanged: every
           ticket started only after its dependencies were merged.
           Earlier this session: audited the previous team's Drive "Camera Roll" (docs/inherited/camera_roll_report.html,
           HANDOVER.md draft, comment on #2). It holds 5,490 unlabelled stills of one print, so T-0002 item 2 is partial.
RESULT:    16 of 24 merged and pushed. DONE (13): T-0011 0014 0016 0019 0020 0021 0022 0026 0027 0029 0031 0033 0035.
           WAITING-GPU (3), each with a runbook in docs/gpu-runs/:
           - T-0023: 100k-case @slow property run, CPU only, under 2 min
           - T-0030: gpu test, needs best.pt
           - T-0037: manual replay check + screenshot
           BLOCKED-SPEC (1): T-0018 (below). Skipped because they depend on T-0018: T-0034 → 0051 → 0036, 0038,
           0052 → 0043 → 0044.
           Main: 174 passed, 3 deselected in 33 s; ruff clean.
SURPRISE:  - T-0018: 07 §11's sign rule "if ΣH < 0 then H ← −H" is degenerate. Ā is row-centred, so ΣĀv₁ ≡ 0 and the
             sign depends on rounding noise. Proposed DESCEND: test Σ(A v₁) instead. Branch t0018 (c1b8ed4)
             implements that and is green, not merged.
           - T-0023 found that gate() rounds half-up after the L2 clip, so a fractional setpoint can exceed the step
             (210.5 + 5 → S216, |Δ| 5.5 > step 5). The 07 §3 invariant |Δ'| ≤ step breaks only for non-integer
             setpoints, which the gate itself never sends. Not fixed: the obvious fix flips the L1 verdict of
             tests/test_gate.py::test_rounding_pushes_over_l1_limit, so it needs a user decision.
           - One full-suite run during the parallel build took 52 min because of CPU contention from the agents'
             processes. With nothing else running it takes 33 s.
           - T-0011 added an additive build_model(..., pretrained=True) flag (tests never download weights).
             T-0016 added make_proposal(..., defect_id='').
BROKE:     Nothing. Added .claude to ruff extend-exclude and .claude/worktrees/ to .gitignore (agent worktrees).
NEXT:      User decision on the T-0018 DESCEND. If approved: edit 07 §11, merge t0018, then a second parallel run for
           T-0034 → 0051 → {0036, 0038, 0052} → 0043 → 0044. T-0002 (HUMAN) is still the critical-path blocker.

## 2026-10-26 — DESCEND (user-approved): 07 §11 EigenCAM sign rule + T-0018 merged
BUILT:     07-math §11: "If ΣH < 0" became "If Σ(A v₁) < 0". Ā is row-centred, so ΣĀv₁ ≡ 0 and the old test was
           float noise. The user approved the change ("approve and start the second run"). Merged branch t0018
           (xqi/explain/attribution.py, tests/test_attribution.py), which already implemented the new rule.
RESULT:    Main: 178 passed, 4 deselected in 100 s; ruff clean. Done-when met: the tiny-CNN quadrant + zero-activation
           tests pass, and the gpu test (test_real_best_pt_heatmap_fast) is written for GPU batch G1 with T-0008.
           No SCHEMA_VERSION bump (math only; types/store/CSVs unchanged).
SURPRISE:  Nothing new.
BROKE:     Nothing.
NEXT:      Parallel run 2: T-0034 → T-0051 → {T-0036, T-0038, T-0052} → T-0043 → T-0044.

## 2026-10-26 — T-0034: Implement the orchestrator's gated-recipe, auto and advisory action paths (parallel run)
BUILT:     xqi/orchestrator.py: the non-critical, non-baseline P3 branch. It runs get_state (a fresh state also goes
           into telemetry/history; _poll became _state), then explain (or recipe_to_proposals in gated-recipe, with no
           cause model and no L4), then gate each proposal, then event_verdict. Proposals and verdicts are written with
           t_gate. PROPOSE and ESCALATE are written pending with deadline_ts = t_gate + hitl.timeout_s, and ESCALATE
           also pauses (a failed pause writes a pause_failed alert). APPLY goes through a new _dispatch: one retry, an
           action row (source auto, proposal_id when there is one), and Verifier.watch only when ok. Baseline now uses
           _dispatch too. EigenCAM runs as a job on a worker thread after dispatch. The worker has its own Store
           connection and writes runs/<id>/heatmaps/<defect_id>.png, defects.heatmap_path and a t_heatmap timing.
           A model_lock serialises detector and heatmap passes on the shared YOLO model.
RESULT:    New tests in tests/test_orchestrator.py: (1) test_modes: a singleton set in auto sends M221 S108 and is
           APPLY; a 2-member set in auto is PROPOSE, pending, with the right deadline; advisory is PROPOSE and sends
           nothing; misalignment is ESCALATE, pending and paused; in gated-recipe the nozzle line is blocked by L2
           cooldown and only the survivors M220 S90 / M221 S110 are sent, with no explanation row.
           (2) test_apply_updates_state: printer flow is 108, last_change_ts is about t_disp, one outcome is logged.
           (3) test_heatmap_after_dispatch: the PNG exists, heatmap_path is set, and t_heatmap > t_disp.
           (4) test_dispatch_failure: 2 send attempts, ok=0, setpoints and last_change_ts unchanged, a dispatch_failed
           alert, and no outcome. Done-when (the mode tests pass) holds. Merged t0034 (4340922) into main with
           --no-ff, no conflicts. `pytest -q` -> 182 passed, 4 deselected in 31 s; ruff clean.
SURPRISE:  - The Windows time.monotonic resolution is coarse enough that an instant stub heatmap tied t_disp exactly.
             The stub eigencam now sleeps 20 ms, like a real pass.
           - Ultralytics YOLO is not safe to share across threads, and the forward hook would catch detector passes
             too. That is why the heatmap job takes model_lock.
           - Spec calls the implementer made: gated-recipe APPLY actions use source "auto" (09 §Store lists
             auto/operator/critical/baseline/timeout); several surviving recipe lines go in one send_gcode call and
             one action row with proposal_id NULL, like baseline, and the verdict row holds the proposal ids.
             Heatmaps are queued only in auto/advisory (P3); FR-009 says "per non-critical confirmed defect", which is
             broader. Mild 06-vs-08 wording gap, not a blocker.
BROKE:     Nothing. One behaviour change: in auto/advisory with no explainer wired, every non-critical defect now
           ESCALATEs (no_confident_cause), which pauses the printer. Before, it did nothing. __main__ still passes
           explainer=None.
NEXT:      Wire the Explainer (CauseModel weights + qhat_file) into xqi/__main__.py (outside this ticket's Files:
           line), so auto/advisory from the CLI stays a fail-safe that escalates every defect until then. Next in
           parallel run 2: T-0051.

## 2026-10-26 — T-0051: Implement operator-decision processing and timeouts in the loop (parallel run)
BUILT:     Orchestrator.process_operator_decisions() and check_timeouts() in xqi/orchestrator.py. The loop calls both on
           every tick, after handle_event and before verifier.tick (08 P1). apply rebuilds the stored Proposal and
           re-gates it on a fresh get_state(). modify builds a new Proposal (cause=operator, id <pid>-op<decision id>)
           with the operator's delta measured from the current setpoint, gates it and writes it to proposals, so
           gate_json holds the clip reason. reject is only logged. pause calls printer.pause() and stop calls
           printer.estop(); both are logged as source=operator actions. Every decision is marked consumed and its
           verdict's pending flag is cleared. Timeouts insert a choice=timeout decision row (operator 'loop',
           latency = now - t_gate), mark it consumed, clear pending and run hitl.timeout_action (pause is logged as a
           source=timeout action).
RESULT:    7 new tests in tests/test_orchestrator.py: test_modify_regated (+15 °C → M104 S215, reason
           'L2: clipped +15 → +5 °C'), test_apply_rechecks_cooldown (a flow change 5 s before → nothing sent,
           decision_blocked alert 'L2: cooldown 5s < 20s'), test_pause_stop, test_timeout[noop|pause],
           test_duplicate_decision_ignored (a double apply, a late modify and an unknown event → one dispatch and 3
           decision_ignored alerts), and test_decisions_processed_in_loop (a decision inserted mid-run is picked up by
           run()). Done-when (the decision tests pass) holds. Merged t0051 (acb589e) into main with --no-ff, no
           conflicts. `pytest -q` -> 189 passed, 4 deselected in 34 s; ruff clean.
SURPRISE:  - 09 §Store says the loop only sets `consumed` on operator_decisions, but the ticket, FR-019 and the
             OperatorDecision choice 'timeout' in 09 §Types need the loop to insert the timeout row. Implemented per
             the ticket and §Types: the loop inserts through insert_decision, under WAL plus busy_timeout. Candidate
             one-line 09 note (needs user approval): "loop also inserts choice=timeout rows (consumed=1)".
           - The store has no clear-pending API, so pending is cleared by rewriting the verdict row with
             write_verdict(pending=False), which keeps t_gate and deadline_ts.
           - apply dispatches the re-gated final_gcode, which equals the stored gated G-code when state is unchanged.
BROKE:     Nothing. The existing 12 orchestrator tests still pass. If the detector raises on a frame, the decision and
           timeout steps are skipped for that frame (the existing `continue`); this is bounded by the 10-failure pause.
NEXT:      Take the next step from SEQUENCE.md. Open item: propose the 09 §Store timeout-row note as a DESCEND.
