"""Tests for setting stock targets from the building page (REQ-15).

The route saves through the Stock Daddy API. The first group of tests
swaps api_client.set_target for a stand-in, so they check the route on its
own. The end-to-end tests at the bottom start the real API on a free port
against a private copy of the database; they're skipped if the API's
requirements (python-dotenv) aren't installed.
"""

import importlib.util
import os
import socket
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import pytest

import api_client
import db
from app import app

OWNER = 1
OTHER_OWNER = 999999
API_DIR = Path(__file__).resolve().parent.parent.parent / "stock_daddy_api"


@pytest.fixture(autouse=True)
def _isolated(fresh_db):
    """Every test here may write, so each gets its own copy of the database."""


def _client(owner_id=OWNER):
    app.config["TESTING"] = True
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user"] = "Test"
        sess["owner_id"] = owner_id
    return client


def _target(building_id, item_type_name):
    row = next(r for r in db.get_building(OWNER, building_id)["compliance"]
               if r["item_type"] == item_type_name)
    return row["target"]


# --- The route on its own ---------------------------------------------------

def test_building_page_shows_set_target_form():
    html = _client().get("/building/1").get_data(as_text=True)
    assert "Set Target" in html
    assert 'name="target_qty"' in html
    assert "Nail Gun" in html


def test_set_target_calls_the_api(monkeypatch):
    calls = []
    monkeypatch.setattr(api_client, "set_target",
                        lambda *args: calls.append(args) or ({}, False))
    resp = _client().post("/building/1/targets",
                          data={"item_type_id": "1", "target_qty": "8"},
                          follow_redirects=True)
    assert calls == [(OWNER, 1, 1, 8)]
    assert "Updated the Nail Gun target to 8." in resp.get_data(as_text=True)


@pytest.mark.parametrize("form", [
    {"item_type_id": "1", "target_qty": "-1"},
    {"item_type_id": "1", "target_qty": "abc"},
    {"item_type_id": "1"},
    {"item_type_id": "999999", "target_qty": "3"},
    {"target_qty": "3"},
])
def test_bad_input_never_reaches_the_api(monkeypatch, form):
    monkeypatch.setattr(api_client, "set_target",
                        lambda *a: pytest.fail("should not call the API"))
    resp = _client().post("/building/1/targets", data=form, follow_redirects=True)
    assert "Pick an item type and enter a target of 0 or more." in resp.get_data(as_text=True)


def test_other_owners_building_redirects_to_dashboard(monkeypatch):
    monkeypatch.setattr(api_client, "set_target",
                        lambda *a: pytest.fail("should not call the API"))
    resp = _client(OTHER_OWNER).post("/building/1/targets",
                                     data={"item_type_id": "1", "target_qty": "8"})
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/dashboard")


def test_api_down_shows_a_message(monkeypatch):
    def down(*args):
        raise api_client.ApiUnavailable("connection refused")
    monkeypatch.setattr(api_client, "set_target", down)
    resp = _client().post("/building/1/targets",
                          data={"item_type_id": "1", "target_qty": "8"},
                          follow_redirects=True)
    assert "Couldn&#39;t reach the Stock Daddy API" in resp.get_data(as_text=True)
    assert _target(1, "Nail Gun") == 3


def test_not_logged_in_redirects_to_login():
    resp = app.test_client().post("/building/1/targets",
                                  data={"item_type_id": "1", "target_qty": "8"})
    assert resp.headers["Location"].endswith("/login")


# --- End to end, through the real API ---------------------------------------

needs_api = pytest.mark.skipif(
    importlib.util.find_spec("dotenv") is None,
    reason="stock_daddy_api requirements not installed",
)


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture
def real_api(fresh_db, monkeypatch):
    """Start stock_daddy_api on a free port, pointed at this test's database."""
    port = _free_port()
    env = dict(os.environ, DB_PATH=str(fresh_db), API_PORT=str(port), FLASK_DEBUG="False")
    proc = subprocess.Popen([sys.executable, "app.py"], cwd=API_DIR, env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    deadline = time.time() + 15
    while time.time() < deadline:
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
            break
        except OSError:
            if proc.poll() is not None:
                pytest.fail("the API exited during startup")
            time.sleep(0.1)
    else:
        proc.kill()
        pytest.fail("the API didn't start in time")
    monkeypatch.setattr(api_client, "API_URL", f"http://127.0.0.1:{port}")
    yield port
    proc.terminate()
    proc.wait(timeout=10)


@needs_api
def test_end_to_end_update_existing_target(real_api, fresh_db):
    resp = _client().post("/building/1/targets",
                          data={"item_type_id": "1", "target_qty": "9"},
                          follow_redirects=True)
    assert "Updated the Nail Gun target to 9." in resp.get_data(as_text=True)
    assert _target(1, "Nail Gun") == 9
    conn = sqlite3.connect(fresh_db)
    count = conn.execute("SELECT COUNT(*) FROM target_quantity "
                         "WHERE building_id = 1 AND item_type_id = 1").fetchone()[0]
    conn.close()
    assert count == 1  # updated, not duplicated


@needs_api
def test_end_to_end_new_target(real_api, fresh_db):
    conn = sqlite3.connect(fresh_db)
    item_type_id = conn.execute("INSERT INTO item_type (name) VALUES ('Test Drill')").lastrowid
    conn.commit()
    conn.close()
    resp = _client().post("/building/1/targets",
                          data={"item_type_id": str(item_type_id), "target_qty": "2"},
                          follow_redirects=True)
    assert "Set the Test Drill target to 2." in resp.get_data(as_text=True)
    assert _target(1, "Test Drill") == 2
