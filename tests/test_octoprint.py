import json
import logging
from pathlib import Path

import pytest
import requests

from xqi.config import load
from xqi.printer import OctoPrintClient, Printer

ROOT = Path(__file__).resolve().parents[1]
CFG = load(ROOT / "config" / "default.yaml")
KEY = "SECRET-KEY-123"

# Recorded from OctoPrint 1.9 GET /api/printer while printing.
PRINTER_JSON = {
    "sd": {"ready": False},
    "state": {
        "error": "",
        "flags": {"operational": True, "paused": False, "printing": True, "ready": True},
        "text": "Printing",
    },
    "temperature": {
        "bed": {"actual": 59.8, "offset": 0, "target": 60.0},
        "tool0": {"actual": 209.6, "offset": 0, "target": 210.0},
    },
}
JOB_JSON = {
    "job": {"file": {"name": "cube.gcode"}},
    "progress": {"completion": 42.5, "printTime": 600, "printTimeLeft": 800},
    "state": "Printing",
}


def _response(status: int, body=None) -> requests.Response:
    r = requests.Response()
    r.status_code = status
    r._content = json.dumps(body or {}).encode()
    return r


class Recorder:
    """Stands in for requests.Session.request; no real network."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def __call__(self, session, method, url, **kwargs):
        self.calls.append((method, url, dict(session.headers), kwargs))
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv(CFG.printer.api_key_env, KEY)
    return OctoPrintClient(CFG, clock=lambda: 100.0)


def _patch(monkeypatch, *replies) -> Recorder:
    rec = Recorder(replies)
    monkeypatch.setattr(requests.Session, "request", lambda s, *a, **kw: rec(s, *a, **kw))
    return rec


def test_is_a_printer(client):
    assert isinstance(client, Printer)


def test_state_parsed_from_recorded_fixture(monkeypatch, client):
    rec = _patch(monkeypatch, _response(200, PRINTER_JSON), _response(200, JOB_JSON))
    s = client.get_state()
    assert (s.ts, s.state) == (100.0, "Printing")
    assert (s.nozzle_actual_c, s.nozzle_target_c) == (209.6, 210.0)
    assert (s.bed_actual_c, s.bed_target_c) == (59.8, 60.0)
    assert (s.flow_pct, s.speed_pct) == (100.0, 100.0)  # cfg.printer.nominal
    assert s.progress_pct == 42.5
    assert [(m, u) for m, u, _, _ in rec.calls] == [
        ("GET", "http://octopi.local/api/printer"),
        ("GET", "http://octopi.local/api/job"),
    ]
    assert all(h["X-Api-Key"] == KEY for _, _, h, _ in rec.calls)
    assert all(kw["timeout"] == CFG.printer.timeout_s for _, _, _, kw in rec.calls)


def test_job_failure_leaves_progress_none(monkeypatch, client):
    _patch(monkeypatch, _response(200, PRINTER_JSON), _response(409), _response(409))
    assert client.get_state().progress_pct is None


def test_printer_failure_raises(monkeypatch, client):
    _patch(monkeypatch, requests.ConnectionError(), requests.ConnectionError())
    with pytest.raises(OSError):
        client.get_state()


def test_send_gcode_posts_exact_body_and_tracks(monkeypatch, client):
    rec = _patch(monkeypatch, _response(204), _response(200, PRINTER_JSON), _response(200, JOB_JSON))
    assert client.send_gcode(["M221 S95", "M220 S90"])
    method, url, _, kw = rec.calls[0]
    assert (method, url) == ("POST", "http://octopi.local/api/printer/command")
    assert kw["json"] == {"commands": ["M221 S95", "M220 S90"]}
    s = client.get_state()
    assert (s.flow_pct, s.speed_pct) == (95.0, 90.0)
    assert s.last_change_ts["flow"] == 100.0
    assert s.last_change_ts["speed"] == 100.0


def test_timeout_returns_false_and_setpoints_unchanged(monkeypatch, client):
    rec = _patch(
        monkeypatch,
        requests.Timeout(),
        requests.Timeout(),
        _response(200, PRINTER_JSON),
        _response(200, JOB_JSON),
    )
    assert client.send_gcode(["M221 S95"]) is False
    assert len(rec.calls) == 2  # one retry
    s = client.get_state()
    assert s.flow_pct == 100.0
    assert "flow" not in s.last_change_ts


def test_connection_error_retried_once(monkeypatch, client):
    rec = _patch(monkeypatch, requests.ConnectionError(), _response(204))
    assert client.send_gcode(["M220 S90"])
    assert len(rec.calls) == 2


def test_pause_resume_estop_bodies(monkeypatch, client):
    rec = _patch(monkeypatch, _response(204), _response(204), _response(204))
    assert client.pause() and client.resume() and client.estop()
    assert [(u.rsplit("/api", 1)[1], kw["json"]) for _, u, _, kw in rec.calls] == [
        ("/job", {"command": "pause", "action": "pause"}),
        ("/job", {"command": "pause", "action": "resume"}),
        ("/printer/command", {"commands": ["M112"]}),
    ]


def test_key_never_logged(monkeypatch, client, caplog):
    caplog.set_level(logging.DEBUG)
    bad = _response(500, {"k": KEY})
    _patch(monkeypatch, requests.ConnectionError(KEY), requests.Timeout(KEY), bad, bad)
    assert client.send_gcode(["M221 S95"]) is False
    assert client.pause() is False
    assert caplog.records  # failures are logged...
    assert KEY not in caplog.text  # ...but never the key
    assert KEY not in repr(client)


def test_missing_key_env_raises(monkeypatch):
    monkeypatch.delenv(CFG.printer.api_key_env, raising=False)
    with pytest.raises(KeyError, match=CFG.printer.api_key_env):
        OctoPrintClient(CFG)
