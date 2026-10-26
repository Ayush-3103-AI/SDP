"""Data access for the dashboard (ADR-0005). All UI SQL lives here; xqi/ui.py is layout only."""

from __future__ import annotations

import os
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from xqi.store import Store
from xqi.types import Detection

DB_NAME = "events.sqlite"
LATEST_FRAME = Path("frames") / "latest.jpg"
FRAME_WIDTH = 640
ALERT_WINDOW_S = 30.0

_EVENTS_SQL = """
SELECT t_conf AS t, 'defect' AS kind, defect_id,
       printf('%s conf=%.2f severity=%.2f', cls, conf, severity) AS message
FROM defects
UNION ALL
SELECT t_gate, 'verdict', defect_id,
       verdict || CASE WHEN pending THEN ' (pending)' ELSE '' END || ': ' || reason
FROM verdicts WHERE t_gate IS NOT NULL
UNION ALL
SELECT t_disp, 'action', defect_id,
       source || ': ' || (SELECT group_concat(value, ' ') FROM json_each(gcode_json))
       || CASE WHEN ok THEN ' ok' ELSE ' FAILED' END
FROM actions
UNION ALL
SELECT ts, 'alert', NULL, kind || ': ' || message
FROM alerts
ORDER BY t DESC
LIMIT ?
"""


def resolve_run(run_dir: str | Path, run: str) -> Path:
    """Path of runs/<run>/events.sqlite; ``latest`` picks the newest DB."""
    run_dir = Path(run_dir)
    if run == "latest":
        dbs = list(run_dir.glob(f"*/{DB_NAME}"))
        if not dbs:
            raise FileNotFoundError(f"no runs under {run_dir}")
        return max(dbs, key=lambda p: p.stat().st_mtime)
    path = run_dir / run / DB_NAME
    if not path.exists():
        raise FileNotFoundError(path)
    return path


def latest_state(store: Store) -> dict[str, Any] | None:
    rows = store.query("SELECT * FROM telemetry ORDER BY ts DESC, id DESC LIMIT 1")
    return rows[0] if rows else None


def run_mode(store: Store) -> str | None:
    rows = store.query("SELECT mode FROM runs LIMIT 1")
    return rows[0]["mode"] if rows else None


def last_events(store: Store, n: int = 50) -> list[dict[str, Any]]:
    """Timeline rows {t, kind, defect_id, message}, newest first."""
    return store.query(_EVENTS_SQL, (n,))


def recent_alerts(store: Store, n: int = 5, window_s: float = ALERT_WINDOW_S) -> list[dict[str, Any]]:
    """Alerts raised within ``window_s`` of the latest telemetry (both on the loop's clock), newest first."""
    return store.query(
        """
        SELECT ts, kind, message FROM alerts
        WHERE ts >= COALESCE((SELECT MAX(ts) FROM telemetry), ts) - ?
        ORDER BY ts DESC, id DESC LIMIT ?
        """,
        (window_s, n),
    )


def save_latest_frame(
    run_path: str | Path,
    image: np.ndarray,
    dets: Sequence[Detection],
    width: int = FRAME_WIDTH,
) -> Path | None:
    """Loop side: write a downscaled frame with boxes to runs/<id>/frames/latest.jpg.

    Written to a temp file and swapped in, so the UI never reads half a JPEG.
    """
    path = Path(run_path) / LATEST_FRAME
    path.parent.mkdir(parents=True, exist_ok=True)

    scale = width / image.shape[1]
    small = cv2.resize(image, (width, round(image.shape[0] * scale)))
    for det in dets:
        x1, y1, x2, y2 = (round(v * scale) for v in det.xyxy)
        cv2.rectangle(small, (x1, y1), (x2, y2), (0, 0, 255), 2)
        cv2.putText(small, f"{det.cls} {det.conf:.2f}", (x1, max(y1 - 4, 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1)

    tmp = path.with_name("latest.tmp.jpg")
    cv2.imwrite(str(tmp), small)
    try:
        os.replace(tmp, path)
    except OSError:
        # Windows refuses the swap while the UI has the file open; the next frame retries.
        return None
    return path
