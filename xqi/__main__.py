"""`python -m xqi <cmd>` (09 §CLI)."""

from __future__ import annotations

import argparse
import logging
from dataclasses import replace
from pathlib import Path

from xqi.camera import open_source
from xqi.config import load
from xqi.detect import Detector
from xqi.orchestrator import Orchestrator, new_run_id
from xqi.printer import FakePrinter, OctoPrintClient
from xqi.store import Store

MODES = ("baseline", "gated-recipe", "auto", "advisory")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m xqi")
    sub = parser.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run", help="run the detection/correction loop")
    run.add_argument("--config", required=True)
    run.add_argument("--mode", choices=MODES, help="overrides cfg.mode")
    run.add_argument("--max-frames", type=int)
    ui = sub.add_parser("ui", help="open the dashboard")
    ui.add_argument("--run", default="latest")
    args = parser.parse_args(argv)

    if args.cmd == "ui":
        from xqi.ui import launch

        return launch(args.run)

    logging.basicConfig(level=logging.INFO)
    cfg = load(args.config)
    if args.mode:
        cfg = replace(cfg, mode=args.mode)
    nominal = cfg.printer.nominal
    if cfg.printer.kind == "fake":
        printer = FakePrinter(nozzle_c=nominal["nozzle_temp"], bed_c=nominal["bed_temp"])
    else:
        printer = OctoPrintClient(cfg)
    d = cfg.detector
    detector = Detector(d.weights, d.imgsz, d.conf, d.device)
    source = open_source(cfg.camera.source, cfg.camera.width, cfg.camera.height)
    store = Store(Path(cfg.run_dir) / new_run_id() / "events.sqlite")
    # Explainer (cause model + conformal) is wired in by T-0034; critical/baseline paths need none.
    Orchestrator(cfg, printer, source, detector, None, store).run(args.max_frames)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
