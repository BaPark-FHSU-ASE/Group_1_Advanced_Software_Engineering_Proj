"""Tests for api_launcher.start_api(), which starts the API with the frontend."""

import importlib.util
import socket
import time

import pytest

import api_client
import api_launcher


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("WERKZEUG_RUN_MAIN", raising=False)
    monkeypatch.delenv("STOCKDADDY_START_API", raising=False)
    # Don't leave a SIGTERM handler or atexit hook from one test in place.
    monkeypatch.setattr(api_launcher.signal, "signal", lambda *a: None)
    monkeypatch.setattr(api_launcher.atexit, "register", lambda *a: None)


def test_skipped_when_turned_off(monkeypatch):
    monkeypatch.setenv("STOCKDADDY_START_API", "0")
    monkeypatch.setattr(api_client, "API_URL", f"http://127.0.0.1:{_free_port()}")
    assert api_launcher.start_api() is None


def test_skipped_in_flask_reloader_child(monkeypatch):
    monkeypatch.setenv("WERKZEUG_RUN_MAIN", "true")
    monkeypatch.setattr(api_client, "API_URL", f"http://127.0.0.1:{_free_port()}")
    assert api_launcher.start_api() is None


def test_skipped_for_api_on_another_machine(monkeypatch):
    monkeypatch.setattr(api_client, "API_URL", "http://example.invalid:5001")
    assert api_launcher.start_api() is None


def test_uses_api_already_running(monkeypatch):
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen()
    port = listener.getsockname()[1]
    monkeypatch.setattr(api_client, "API_URL", f"http://127.0.0.1:{port}")
    try:
        assert api_launcher.start_api() is None
    finally:
        listener.close()


def test_api_that_fails_to_start_only_warns(monkeypatch, tmp_path, capsys):
    (tmp_path / "app.py").write_text("raise SystemExit('missing requirements')\n")
    monkeypatch.setattr(api_launcher, "API_DIR", tmp_path)
    monkeypatch.setattr(api_client, "API_URL", f"http://127.0.0.1:{_free_port()}")
    assert api_launcher.start_api() is None
    assert "Everything except Set Target still works" in capsys.readouterr().err


@pytest.mark.skipif(importlib.util.find_spec("dotenv") is None,
                    reason="stock_daddy_api requirements not installed")
def test_starts_and_stops_the_real_api(monkeypatch, fresh_db):
    port = _free_port()
    monkeypatch.setattr(api_client, "API_URL", f"http://127.0.0.1:{port}")
    proc = api_launcher.start_api()
    assert proc is not None
    try:
        target, created = api_client.set_target(1, 1, 1, 6)
        assert target["target_qty"] == 6 and created is False
    finally:
        api_launcher._stop(proc)
    time.sleep(0.2)
    assert not api_launcher._port_open("127.0.0.1", port)
