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
