# CLAUDE.md — SDP: Explainable, safe human-in-the-loop correction for FFF printing

This repo implements a UG-scale piece of CARR Topic 4.1.3 (deck: `context`). The project's memory is `project-context/`; the code is its output.

## Every session (one ticket per session)
1. Read `project-context/STATE.md` and `project-context/11-tickets/SEQUENCE.md`. The ticket to do is the lowest-numbered step that isn't DONE in BOARD.md, applying SEQUENCE.md's skip rules if it's blocked. Read that ticket.
2. Read **only** the context sections the ticket's `Context:` line names. Don't open other spec files "just in case".
3. Check the ticket's `Depends on:` are DONE in `11-tickets/BOARD.md`. If not, stop and say which ones are blocking.
4. Owner HUMAN → don't execute it; tell the user what they need to do. Owner PAIR → do the CODE part, then hand the human their part with exact commands.
5. Build test-first: write the ticket's `Test:` first, see it fail, then implement.
6. Run `uv run pytest` (default markers exclude gpu/hw/slow) and `uv run ruff check .`. Done means the ticket's `Done when:` is observably true. "Mostly working" is not done.
7. Append a LOGBOOK.md entry (BUILT / RESULT / SURPRISE / BROKE / NEXT). Fully rewrite STATE.md (< 200 lines). Update the ticket's row in BOARD.md. Commit with message `T-00NN: <title> (closes #NN)` and push. GitHub issue #NN is ticket T-00NN in github.com/Ayush-3103-AI/SDP. For HUMAN/PAIR tickets, comment progress on the issue with `gh issue comment NN`.
8. Stop. Report the outcome and name the next step from SEQUENCE.md. Do not start it. Never reorder SEQUENCE.md without the user's approval.

## Hard rules
- **Never feed setpoints or telemetry into the cause model** (ADR-0002). `CauseModel.predict` takes only (crop, defect).
- **Never send printer commands outside `gate()`**, except the critical-class estop/pause and baseline mode. The UI never talks to OctoPrint.
- **Never edit `data/splits/logo.json`** after T-0007, and never tune anything on test folds.
- **Never send heater, motion or M112 commands from a script against a real printer** unless the ticket says so and the user is present.
- **If a ticket reveals a spec error**, stop and propose a DESCEND (edit `06`–`09` only with the user's approval). Don't patch around it.
- **Kill criteria K1 (T-0006), K2 (T-0013), K3 (week 6):** when one fires, report it and stop. Don't push on.
- Breaking change to `xqi/types.py`, the store schema or the data CSVs → bump `SCHEMA_VERSION` and log a DESCEND.
- Secrets: the OctoPrint key comes from the env var `XQI_OCTOPRINT_KEY`. Never write it to files or logs.
- Write code that reads like the code around it. Smallest diff that meets `Done when`. No new dependency if stdlib or an installed one does it.

## Commands
- Tests: `uv run pytest` · slow: `uv run pytest -m slow` · GPU: `uv run pytest -m gpu` · hardware: `uv run pytest -m hw`
- Lint: `uv run ruff check .`
- Run the loop: `uv run python -m xqi run --config config/default.yaml --mode advisory`
- Dashboard: `uv run python -m xqi ui --run latest`

## Environment
- Dev machine: Windows 11, Python 3.11. The rig laptop has an RTX 3050 (4 GB VRAM).
- Install torch on the rig laptop from the CUDA wheel index, e.g. `uv pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121`. Verify with `torch.cuda.is_available()`.
- Large inherited files (`*.zip`, `AM_*_Model_*.pt/`) are old YOLOv8n models. They are not the deck's YOLO11-S; ignore them.
