"""T-0027 — the OctoPrint REST client, with the HTTP layer mocked."""

from __future__ import annotations

import logging

import pytest
import requests

from xqi.printer import OctoPrintClient, PrinterError

URL = "http://octopi.test"

PRINTER_JSON = {
    "temperature": {
        "tool0": {"actual": 210.4, "target": 210.0, "offset": 0},
        "bed": {"actual": 59.8, "target": 60.0, "offset": 0},
    },
    "sd": {"ready": True},
    "state": {"text": "Printing", "flags": {"printing": True}},
}
JOB_JSON = {"progress": {"completion": 42.5, "printTimeLeft": 1234}}


class FakeResponse:
    def __init__(self, status_code: int = 200, payload=None) -> None:
        self.status_code = status_code
        self._payload = payload

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 400

    def json(self):
        return self._payload


class MalformedResponse(FakeResponse):
    def json(self):
        raise ValueError("not json")


def install(monkeypatch, handler):
    """Route every ``requests.Session.request`` through ``handler``."""

    calls: list[tuple[str, str, dict]] = []

    def request(self, method, url, **kwargs):
        calls.append((method, url, kwargs))
        return handler(method, url, kwargs)

    monkeypatch.setattr(requests.Session, "request", request)
    return calls


def route(printer=None, job=None, command=None):
    def handler(method, url, _kwargs):
        if url.endswith("/api/printer/command"):
            return command if command is not None else FakeResponse(200, None)
        if url.endswith("/api/printer"):
            return printer if printer is not None else FakeResponse(200, PRINTER_JSON)
        if url.endswith("/api/job"):
            return job if job is not None else FakeResponse(200, JOB_JSON)
        return FakeResponse(200, None)

    return handler


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("XQI_OCTOPRINT_KEY", raising=False)
    return OctoPrintClient(
        url=URL,
        api_key_env="XQI_OCTOPRINT_KEY",
        timeout_s=0.5,
        nominal={"flow": 100, "speed": 100},
    )


def test_state_is_parsed_from_printer_and_job(monkeypatch, client):
    install(monkeypatch, route())

    state = client.get_state()

    assert state.state == "Printing"
    assert state.nozzle_actual_c == pytest.approx(210.4)
    assert state.nozzle_target_c == pytest.approx(210.0)
    assert state.bed_actual_c == pytest.approx(59.8)
    assert state.bed_target_c == pytest.approx(60.0)
    assert state.progress_pct == pytest.approx(42.5)
    assert state.flow_pct == 100
    assert state.speed_pct == 100


def test_send_gcode_posts_the_exact_command_body(monkeypatch, client):
    calls = install(monkeypatch, route())

    assert client.send_gcode(["M104 S220"]) is True

    method, url, kwargs = calls[0]
    assert method == "POST"
    assert url == f"{URL}/api/printer/command"
    assert kwargs["json"] == {"commands": ["M104 S220"]}
    assert kwargs["timeout"] == 0.5


def test_successful_sends_track_flow_and_speed(monkeypatch, client):
    install(monkeypatch, route())

    client.send_gcode(["M221 S110", "M220 S80"])

    state = client.get_state()
    assert state.flow_pct == 110
    assert state.speed_pct == 80
    assert "flow" in state.last_change_ts
    assert "speed" in state.last_change_ts


def test_estop_sends_m112(monkeypatch, client):
    calls = install(monkeypatch, route())

    assert client.estop() is True

    assert calls[0][2]["json"] == {"commands": ["M112"]}


def test_timeout_returns_false_and_leaves_setpoints_unchanged(monkeypatch, client):
    def handler(method, url, _kwargs):
        raise requests.Timeout("slow")

    install(monkeypatch, handler)

    assert client.send_gcode(["M221 S120"]) is False
    assert client.flow_pct == 100
    assert client.last_change_ts == {}


def test_timeout_is_not_retried(monkeypatch, client):
    calls = install(monkeypatch, lambda *_: (_ for _ in ()).throw(requests.Timeout()))

    assert client.send_gcode(["M104 S220"]) is False
    assert len(calls) == 1


def test_connection_error_is_retried_once(monkeypatch, client):
    attempts = {"n": 0}

    def handler(method, url, _kwargs):
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise requests.ConnectionError("refused")
        return FakeResponse(200, None)

    calls = install(monkeypatch, handler)

    assert client.send_gcode(["M104 S220"]) is True
    assert len(calls) == 2


def test_connection_error_twice_returns_false(monkeypatch, client):
    calls = install(
        monkeypatch,
        lambda *_: (_ for _ in ()).throw(requests.ConnectionError("refused")),
    )

    assert client.send_gcode(["M104 S220"]) is False
    assert len(calls) == 2


@pytest.mark.parametrize("status", [400, 401, 403, 404, 500, 503])
def test_http_error_statuses_fail(monkeypatch, client, status):
    error = FakeResponse(status, None)
    install(monkeypatch, route(printer=error, command=error, job=error))

    assert client.send_gcode(["M104 S220"]) is False
    with pytest.raises(PrinterError):
        client.get_state()


def test_malformed_json_raises(monkeypatch, client):
    install(monkeypatch, route(printer=MalformedResponse(200)))

    with pytest.raises(PrinterError):
        client.get_state()


def test_missing_temperature_raises(monkeypatch, client):
    install(monkeypatch, route(printer=FakeResponse(200, {"state": {"text": "Printing"}})))

    with pytest.raises(PrinterError):
        client.get_state()


def test_missing_tool_field_raises(monkeypatch, client):
    payload = {
        "temperature": {"tool0": {"actual": 210.0, "target": 210.0}},
        "state": {"text": "Printing"},
    }
    install(monkeypatch, route(printer=FakeResponse(200, payload)))

    with pytest.raises(PrinterError):
        client.get_state()


def test_unavailable_job_still_yields_state(monkeypatch, client):
    install(monkeypatch, route(job=FakeResponse(500, None)))

    state = client.get_state()
    assert state.state == "Printing"
    assert state.progress_pct is None


def test_unavailable_state_sends_no_command(monkeypatch, client):
    calls = install(monkeypatch, route(printer=FakeResponse(503, None)))

    with pytest.raises(PrinterError):
        client.get_state()

    assert all(method != "POST" for method, _, _ in calls)


def test_pause_and_resume_post_job_actions(monkeypatch, client):
    calls = install(monkeypatch, route())

    assert client.pause() is True
    assert client.resume() is True

    assert calls[0][2]["json"] == {"command": "pause", "action": "pause"}
    assert calls[1][2]["json"] == {"command": "pause", "action": "resume"}


def test_api_key_is_sent_in_the_header(monkeypatch):
    monkeypatch.setenv("XQI_OCTOPRINT_KEY", "secret-key")

    client = OctoPrintClient(URL, "XQI_OCTOPRINT_KEY", 0.5)

    assert client._session.headers["X-Api-Key"] == "secret-key"


def test_api_key_is_never_logged(monkeypatch, caplog):
    monkeypatch.setenv("XQI_OCTOPRINT_KEY", "super-secret-key")
    caplog.set_level(logging.DEBUG, logger="xqi.printer")

    client = OctoPrintClient(URL, "XQI_OCTOPRINT_KEY", 0.5)
    install(monkeypatch, lambda *_: (_ for _ in ()).throw(requests.Timeout()))

    client.send_gcode(["M104 S220"])

    assert "super-secret-key" not in caplog.text


def test_all_traffic_goes_through_the_mocked_session(monkeypatch, client):
    """No real network: every request is the monkeypatched Session.request."""

    calls = install(monkeypatch, route())

    client.get_state()

    assert {url for _, url, _ in calls} == {f"{URL}/api/printer", f"{URL}/api/job"}
