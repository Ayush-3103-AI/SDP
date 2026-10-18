"""``python -m xqi`` — the command line (09-interfaces.md §CLI).

Currently one command: ``run --config C [--mode M] [--max-frames N]``. The
printer and detector backends come from the config (``printer.kind``,
``detector.kind``); nothing here reaches the network or a camera unless the
chosen config says so.
"""

from __future__ import annotations

import argparse
import dataclasses
import sys
from datetime import UTC, datetime
from pathlib import Path

from xqi.camera import open_source
from xqi.config import Config, ConfigError, load
from xqi.detect import Detector, ReplayDetector
from xqi.orchestrator import Orchestrator
from xqi.printer import FakePrinter, OctoPrintClient
from xqi.store import Store

_MODES = ("baseline", "gated-recipe", "auto", "advisory")

_EXIT_OK = 0
_EXIT_ERROR = 1


def _build_printer(cfg: Config):
    kind = cfg.printer.kind

    if kind == "fake":
        return FakePrinter(nominal=cfg.printer.nominal)

    if kind == "octoprint":
        return OctoPrintClient(
            url=cfg.printer.url,
            api_key_env=cfg.printer.api_key_env,
            timeout_s=cfg.printer.timeout_s,
            nominal=cfg.printer.nominal,
        )

    raise ConfigError(f"printer.kind: unknown kind {kind!r}")


def _build_detector(cfg: Config):
    if cfg.detector.kind == "replay":
        return ReplayDetector.from_file(cfg.detector.weights, conf=cfg.detector.conf)

    if cfg.detector.kind == "yolo":
        return Detector(
            cfg.detector.weights,
            cfg.detector.imgsz,
            cfg.detector.conf,
            cfg.detector.device,
        )

    raise ConfigError(f"detector.kind: unknown kind {cfg.detector.kind!r}")


def _run(args: argparse.Namespace) -> int:
    try:
        cfg = load(args.config)
    except ConfigError as exc:
        print(f"config error: {exc}", file=sys.stderr)
        return _EXIT_ERROR

    if args.mode is not None:
        cfg = dataclasses.replace(cfg, mode=args.mode)

    if args.max_frames is not None and args.max_frames < 0:
        print("--max-frames must be >= 0", file=sys.stderr)
        return _EXIT_ERROR

    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    db_path = Path(cfg.run_dir) / run_id / "events.sqlite"

    store = Store(db_path)

    try:
        printer = _build_printer(cfg)
        detector = _build_detector(cfg)
        source = open_source(cfg.camera.source, cfg.camera.width, cfg.camera.height)
        orchestrator = Orchestrator(cfg, printer, source, detector, None, store)
        orchestrator.run(max_frames=args.max_frames)
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        store.close()
        return _EXIT_ERROR
    except Exception as exc:  # noqa: BLE001 - report and exit non-zero
        print(f"run failed: {exc}", file=sys.stderr)
        store.close()
        return _EXIT_ERROR

    print(f"run_id={run_id}")
    print(f"events={db_path}")
    return _EXIT_OK


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="xqi", description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="run the correction loop")
    run_parser.add_argument("--config", required=True, help="path to a YAML config")
    run_parser.add_argument("--mode", choices=_MODES, default=None)
    run_parser.add_argument("--max-frames", type=int, default=None)

    args = parser.parse_args(argv)

    if args.command == "run":
        return _run(args)

    parser.error(f"unknown command: {args.command}")
    return _EXIT_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
