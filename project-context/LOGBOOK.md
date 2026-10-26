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
