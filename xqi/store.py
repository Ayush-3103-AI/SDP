from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping, Sequence
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Self

from xqi.types import (
    SCHEMA_VERSION,
    CauseEstimate,
    CauseSet,
    ConfirmedDefect,
    Detection,
    EventVerdict,
    GateDecision,
    OperatorDecision,
    Outcome,
    PrinterState,
    Proposal,
)

DETECTION_BATCH_SIZE = 25
BUSY_TIMEOUT_MS = 2000


class Store:
    """SQLite event store for one XQI run.

    The main loop owns normal event writes. The UI may only insert
    operator decisions through ``insert_decision``.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

        self.run_id = self.path.parent.name
        self._detection_buffer: list[tuple[Detection, float]] = []
        self._closed = False

        self._conn = self._connect(readonly=False)
        self._create_schema()

    @classmethod
    def open_readonly(cls, path: str | Path) -> Store:
        """Open a store for UI access.

        The returned Store uses a read-only connection for normal queries.
        ``insert_decision`` uses a separate short-lived write connection,
        which is the only write operation exposed to the UI.
        """

        obj = cls.__new__(cls)
        obj.path = Path(path)
        obj.run_id = obj.path.parent.name
        obj._detection_buffer = []
        obj._closed = False
        obj._conn = obj._connect(readonly=True)
        obj._create_write_connection = True
        return obj

    def _connect(self, *, readonly: bool) -> sqlite3.Connection:
        if readonly:
            uri = f"file:{self.path.resolve()}?mode=ro"
            conn = sqlite3.connect(
                uri,
                uri=True,
                timeout=BUSY_TIMEOUT_MS / 1000,
                check_same_thread=False,
            )
        else:
            conn = sqlite3.connect(
                self.path,
                timeout=BUSY_TIMEOUT_MS / 1000,
                check_same_thread=False,
            )
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")

        conn.row_factory = sqlite3.Row
        conn.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
        return conn

    def _write_conn(self) -> sqlite3.Connection:
        if not getattr(self, "_create_write_connection", False):
            return self._conn

        conn = sqlite3.connect(
            self.path,
            timeout=BUSY_TIMEOUT_MS / 1000,
            check_same_thread=False,
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
        return conn

    def _create_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                schema_version INTEGER NOT NULL,
                mode TEXT NOT NULL,
                cfg_json TEXT NOT NULL,
                git_sha TEXT,
                started_iso TEXT,
                ended_iso TEXT
            );

            CREATE TABLE IF NOT EXISTS detections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                schema_version INTEGER NOT NULL,
                run_id TEXT NOT NULL,
                frame_id INTEGER NOT NULL,
                ts REAL NOT NULL,
                cls TEXT NOT NULL,
                conf REAL NOT NULL,
                x1 REAL NOT NULL,
                y1 REAL NOT NULL,
                x2 REAL NOT NULL,
                y2 REAL NOT NULL,
                area_frac REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                schema_version INTEGER NOT NULL,
                run_id TEXT NOT NULL,
                ts REAL NOT NULL,
                state TEXT NOT NULL,
                nozzle_actual_c REAL NOT NULL,
                nozzle_target_c REAL NOT NULL,
                bed_actual_c REAL NOT NULL,
                bed_target_c REAL NOT NULL,
                flow_pct REAL NOT NULL,
                speed_pct REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS defects (
                defect_id TEXT PRIMARY KEY,
                schema_version INTEGER NOT NULL,
                run_id TEXT NOT NULL,
                cls TEXT NOT NULL,
                frame_id INTEGER NOT NULL,
                t0 REAL NOT NULL,
                t_conf REAL NOT NULL,
                conf REAL NOT NULL,
                bbox_json TEXT NOT NULL,
                severity REAL NOT NULL,
                critical INTEGER NOT NULL,
                crop_path TEXT,
                heatmap_path TEXT
            );

            CREATE TABLE IF NOT EXISTS explanations (
                defect_id TEXT PRIMARY KEY,
                schema_version INTEGER NOT NULL,
                run_id TEXT NOT NULL,
                probs_json TEXT NOT NULL,
                set_json TEXT NOT NULL,
                qhat REAL NOT NULL,
                flags_json TEXT NOT NULL,
                t_cause REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS proposals (
                proposal_id TEXT PRIMARY KEY,
                schema_version INTEGER NOT NULL,
                run_id TEXT NOT NULL,
                defect_id TEXT NOT NULL,
                cause TEXT NOT NULL,
                var TEXT NOT NULL,
                from_value REAL NOT NULL,
                delta REAL NOT NULL,
                to_value REAL NOT NULL,
                gcode_json TEXT NOT NULL,
                counterfactual TEXT NOT NULL,
                gate_json TEXT,
                passed INTEGER
            );

            CREATE TABLE IF NOT EXISTS verdicts (
                defect_id TEXT PRIMARY KEY,
                schema_version INTEGER NOT NULL,
                run_id TEXT NOT NULL,
                verdict TEXT NOT NULL,
                reason TEXT NOT NULL,
                proposal_ids_json TEXT NOT NULL,
                t_gate REAL,
                pending INTEGER NOT NULL DEFAULT 0,
                deadline_ts REAL
            );

            CREATE TABLE IF NOT EXISTS operator_decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                schema_version INTEGER NOT NULL,
                run_id TEXT NOT NULL,
                defect_id TEXT NOT NULL,
                proposal_id TEXT,
                choice TEXT NOT NULL,
                modified_delta REAL,
                operator TEXT NOT NULL,
                wall_iso TEXT NOT NULL,
                latency_s REAL NOT NULL,
                consumed INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS actions (
                action_id TEXT PRIMARY KEY,
                schema_version INTEGER NOT NULL,
                run_id TEXT NOT NULL,
                defect_id TEXT NOT NULL,
                proposal_id TEXT,
                source TEXT NOT NULL,
                gcode_json TEXT NOT NULL,
                t_disp REAL NOT NULL,
                ok INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS outcomes (
                action_id TEXT PRIMARY KEY,
                schema_version INTEGER NOT NULL,
                run_id TEXT NOT NULL,
                defect_id TEXT NOT NULL,
                cls TEXT NOT NULL,
                verdict TEXT NOT NULL,
                r_before REAL NOT NULL,
                r_after REAL NOT NULL,
                window_s REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS timings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                schema_version INTEGER NOT NULL,
                run_id TEXT NOT NULL,
                defect_id TEXT NOT NULL,
                stage TEXT NOT NULL,
                t REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                schema_version INTEGER NOT NULL,
                run_id TEXT NOT NULL,
                ts REAL NOT NULL,
                kind TEXT NOT NULL,
                message TEXT NOT NULL
            );
            """
        )
        self._conn.commit()

    @staticmethod
    def _json(value: Any) -> str:
        if is_dataclass(value):
            value = asdict(value)
        return json.dumps(value, separators=(",", ":"))

    @staticmethod
    def _row_dict(row: sqlite3.Row) -> dict[str, Any]:
        return dict(row)

    def _base(self) -> tuple[int, str]:
        return SCHEMA_VERSION, self.run_id

    def write_run(self, obj: Mapping[str, Any] | Any) -> None:
        data = self._object_dict(obj)

        run_id = str(data.get("run_id", self.run_id))

        self._conn.execute(
            """
            INSERT OR REPLACE INTO runs (
                run_id, schema_version, mode, cfg_json,
                git_sha, started_iso, ended_iso
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                SCHEMA_VERSION,
                str(data["mode"]),
                self._json(data.get("cfg_json", data.get("cfg", {}))),
                data.get("git_sha"),
                data.get("started_iso"),
                data.get("ended_iso"),
            ),
        )
        self._conn.commit()

    def write_detection(self, obj: Detection, ts: float) -> None:
        """Buffer a detection; ``ts`` is its Frame.ts (Detection has none)."""
        self._detection_buffer.append((obj, ts))

        if len(self._detection_buffer) >= DETECTION_BATCH_SIZE:
            self.flush_detections()

    def flush_detections(self) -> None:
        if not self._detection_buffer:
            return

        schema_version, run_id = self._base()

        rows = []
        for obj, ts in self._detection_buffer:
            x1, y1, x2, y2 = obj.xyxy
            rows.append(
                (
                    schema_version,
                    run_id,
                    obj.frame_id,
                    ts,
                    obj.cls,
                    obj.conf,
                    x1,
                    y1,
                    x2,
                    y2,
                    obj.area_frac,
                )
            )

        self._conn.executemany(
            """
            INSERT INTO detections (
                schema_version, run_id, frame_id, ts, cls, conf,
                x1, y1, x2, y2, area_frac
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        self._conn.commit()
        self._detection_buffer.clear()

    def write_telemetry(self, obj: PrinterState) -> None:
        schema_version, run_id = self._base()

        self._conn.execute(
            """
            INSERT INTO telemetry (
                schema_version, run_id, ts, state,
                nozzle_actual_c, nozzle_target_c,
                bed_actual_c, bed_target_c,
                flow_pct, speed_pct
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                schema_version,
                run_id,
                obj.ts,
                obj.state,
                obj.nozzle_actual_c,
                obj.nozzle_target_c,
                obj.bed_actual_c,
                obj.bed_target_c,
                obj.flow_pct,
                obj.speed_pct,
            ),
        )
        self._conn.commit()

    def write_defect(
        self,
        obj: ConfirmedDefect,
        *,
        crop_path: str | None = None,
        heatmap_path: str | None = None,
    ) -> None:
        schema_version, run_id = self._base()

        self._conn.execute(
            """
            INSERT OR REPLACE INTO defects (
                defect_id, schema_version, run_id, cls, frame_id,
                t0, t_conf, conf, bbox_json, severity, critical,
                crop_path, heatmap_path
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                obj.defect_id,
                schema_version,
                run_id,
                obj.cls,
                obj.frame_id,
                obj.t0,
                obj.t_conf,
                obj.conf,
                self._json(obj.xyxy),
                obj.severity,
                int(obj.critical),
                crop_path,
                heatmap_path,
            ),
        )
        self._conn.commit()

    def write_explanation(
        self,
        defect_id: str,
        estimate: CauseEstimate,
        cause_set: CauseSet,
        qhat: float,
        flags: Sequence[str],
        t_cause: float,
    ) -> None:
        schema_version, run_id = self._base()

        self._conn.execute(
            """
            INSERT OR REPLACE INTO explanations (
                defect_id, schema_version, run_id,
                probs_json, set_json, qhat, flags_json, t_cause
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                defect_id,
                schema_version,
                run_id,
                self._json(estimate.probs),
                self._json(cause_set.members),
                qhat,
                self._json(list(flags)),
                t_cause,
            ),
        )
        self._conn.commit()

    def write_proposal(
        self,
        obj: Proposal,
        gate: GateDecision | Mapping[str, Any] | None = None,
    ) -> None:
        schema_version, run_id = self._base()

        gate_json = None
        passed = None

        if gate is not None:
            gate_json = self._json(gate)
            if isinstance(gate, GateDecision):
                passed = int(gate.passed)
            elif isinstance(gate, Mapping):
                passed = int(bool(gate.get("passed")))

        self._conn.execute(
            """
            INSERT OR REPLACE INTO proposals (
                proposal_id, schema_version, run_id,
                defect_id, cause, var, from_value, delta, to_value,
                gcode_json, counterfactual, gate_json, passed
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                obj.proposal_id,
                schema_version,
                run_id,
                obj.defect_id,
                obj.cause,
                obj.var,
                obj.from_value,
                obj.delta,
                obj.to_value,
                self._json(obj.gcode),
                obj.counterfactual,
                gate_json,
                passed,
            ),
        )
        self._conn.commit()

    def write_verdict(
        self,
        obj: EventVerdict,
        *,
        t_gate: float | None = None,
        pending: bool = False,
        deadline_ts: float | None = None,
    ) -> None:
        schema_version, run_id = self._base()

        self._conn.execute(
            """
            INSERT OR REPLACE INTO verdicts (
                defect_id, schema_version, run_id,
                verdict, reason, proposal_ids_json,
                t_gate, pending, deadline_ts
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                obj.defect_id,
                schema_version,
                run_id,
                obj.verdict,
                obj.reason,
                self._json(obj.proposal_ids),
                t_gate,
                int(pending),
                deadline_ts,
            ),
        )
        self._conn.commit()

    def insert_decision(self, obj: OperatorDecision | Mapping[str, Any]) -> int:
        """Insert an operator decision.

        This is the only write operation intended for the UI connection.
        """

        data = self._object_dict(obj)
        conn = self._write_conn()

        try:
            cursor = conn.execute(
                """
                INSERT INTO operator_decisions (
                    schema_version, run_id, defect_id, proposal_id,
                    choice, modified_delta, operator, wall_iso,
                    latency_s, consumed
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                """,
                (
                    SCHEMA_VERSION,
                    self.run_id,
                    data["defect_id"],
                    data.get("proposal_id"),
                    data["choice"],
                    data.get("modified_delta"),
                    data["operator"],
                    data["wall_iso"],
                    data["latency_s"],
                ),
            )
            conn.commit()
            return int(cursor.lastrowid)
        finally:
            if conn is not self._conn:
                conn.close()

    def write_operator_decision(
        self,
        obj: OperatorDecision | Mapping[str, Any],
    ) -> int:
        return self.insert_decision(obj)

    def write_action(
        self,
        action_id: str,
        defect_id: str,
        proposal_id: str | None,
        source: str,
        gcode: Sequence[str],
        t_disp: float,
        ok: bool,
    ) -> None:
        schema_version, run_id = self._base()

        self._conn.execute(
            """
            INSERT OR REPLACE INTO actions (
                action_id, schema_version, run_id,
                defect_id, proposal_id, source,
                gcode_json, t_disp, ok
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                action_id,
                schema_version,
                run_id,
                defect_id,
                proposal_id,
                source,
                self._json(list(gcode)),
                t_disp,
                int(ok),
            ),
        )
        self._conn.commit()

    def write_outcome(self, obj: Outcome) -> None:
        schema_version, run_id = self._base()

        self._conn.execute(
            """
            INSERT OR REPLACE INTO outcomes (
                action_id, schema_version, run_id,
                defect_id, cls, verdict,
                r_before, r_after, window_s
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                obj.action_id,
                schema_version,
                run_id,
                obj.defect_id,
                obj.cls,
                obj.verdict,
                obj.r_before,
                obj.r_after,
                obj.window_s,
            ),
        )
        self._conn.commit()

    def write_timing(
        self,
        defect_id: str,
        stage: str,
        t: float,
    ) -> None:
        schema_version, run_id = self._base()

        self._conn.execute(
            """
            INSERT INTO timings (
                schema_version, run_id, defect_id, stage, t
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                schema_version,
                run_id,
                defect_id,
                stage,
                t,
            ),
        )
        self._conn.commit()

    def write_alert(
        self,
        ts: float,
        kind: str,
        message: str,
    ) -> None:
        schema_version, run_id = self._base()

        self._conn.execute(
            """
            INSERT INTO alerts (
                schema_version, run_id, ts, kind, message
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                schema_version,
                run_id,
                ts,
                kind,
                message,
            ),
        )
        self._conn.commit()

    def pending_events(self) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT *
            FROM verdicts
            WHERE run_id = ?
              AND pending = 1
            ORDER BY rowid
            """,
            (self.run_id,),
        ).fetchall()

        return [self._row_dict(row) for row in rows]

    def new_decisions(self) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT *
            FROM operator_decisions
            WHERE run_id = ?
              AND consumed = 0
            ORDER BY id
            """,
            (self.run_id,),
        ).fetchall()

        return [self._row_dict(row) for row in rows]

    def mark_consumed(self, decision_id: int) -> None:
        self._conn.execute(
            """
            UPDATE operator_decisions
            SET consumed = 1
            WHERE id = ?
              AND run_id = ?
            """,
            (decision_id, self.run_id),
        )
        self._conn.commit()

    def query(
        self,
        sql: str,
        params: Sequence[Any] | Mapping[str, Any] = (),
    ) -> list[dict[str, Any]]:
        """Execute a read-only SQL query."""

        normalized = sql.lstrip().upper()

        if not normalized.startswith(
            ("SELECT", "WITH", "PRAGMA", "EXPLAIN")
        ):
            raise ValueError("Store.query() is read-only")

        rows = self._conn.execute(sql, params).fetchall()
        return [self._row_dict(row) for row in rows]

    def flush(self) -> None:
        self.flush_detections()

    def close(self) -> None:
        if self._closed:
            return

        self.flush_detections()
        self._conn.close()
        self._closed = True

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    @staticmethod
    def _object_dict(obj: Mapping[str, Any] | Any) -> dict[str, Any]:
        if isinstance(obj, Mapping):
            return dict(obj)

        if is_dataclass(obj):
            return asdict(obj)

        if hasattr(obj, "__dict__"):
            return dict(vars(obj))

        raise TypeError(
            f"Unsupported object type: {type(obj).__name__}"
        )