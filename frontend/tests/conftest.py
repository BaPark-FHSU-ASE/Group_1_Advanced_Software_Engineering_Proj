"""
Points the whole test session at a disposable copy of the database instead
of the real stockdaddy.db, the same pattern used in
stock_daddy_api/tests/conftest.py.

The frontend never opens the database itself any more, but the schema
tests (via tests/schema_db.py) and the end-to-end tests (via the real API)
do. Both read DB_PATH, so this sets it before anything is imported, which
conftest.py running first, before test collection, guarantees.
"""

import os
import shutil
import tempfile
from pathlib import Path

_REAL_DB = Path(__file__).resolve().parent.parent / "stockdaddy.db"

_tmp_dir = tempfile.mkdtemp(prefix="stockdaddy_frontend_test_")
_tmp_db_path = Path(_tmp_dir) / "stockdaddy_test.db"
shutil.copyfile(_REAL_DB, _tmp_db_path)

os.environ["DB_PATH"] = str(_tmp_db_path)


def pytest_sessionfinish(session, exitstatus):
    shutil.rmtree(_tmp_dir, ignore_errors=True)


import pytest


@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    """A private copy of the database for one test.

    Tests that write use this so they can't change the pinned seed-data
    counts other tests check, whatever order they run in. Pass it to
    real_api to point the API at it.
    """
    from tests import schema_db

    path = tmp_path / "stockdaddy_fresh.db"
    shutil.copyfile(_REAL_DB, path)
    monkeypatch.setattr(schema_db, "DB_PATH", str(path))
    return path


# --- A stand-in for the API, for page tests --------------------------------

import copy
import inspect

import api_client


class FakeApi:
    """Replaces every function in api_client with a recorder.

    api.returns["get_dashboard"] = [...]   what a call gives back (a value,
                                           or a function of the call's args)
    api.fail("retire_room", 409, "msg")    make a call raise ApiError
    api.called("retire_room")              the args each call got, in order
    """

    def __init__(self, monkeypatch):
        self.calls = []
        self.returns = {}
        self.errors = {}
        for name, fn in inspect.getmembers(api_client, inspect.isfunction):
            if not name.startswith("_") and fn.__module__ == "api_client":
                monkeypatch.setattr(api_client, name, self._recorder(name))

    def _recorder(self, name):
        def record(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            if name in self.errors:
                raise self.errors[name]
            value = self.returns.get(name)
            return value(*args, **kwargs) if callable(value) else copy.deepcopy(value)
        return record

    def fail(self, name, status, message="The API said no"):
        self.errors[name] = api_client.ApiError(status, message)

    def unreachable(self, name):
        self.errors[name] = api_client.ApiUnavailable("connection refused")

    def called(self, name):
        return [args + ((kwargs,) if kwargs else ()) for n, args, kwargs in self.calls if n == name]


@pytest.fixture
def api(monkeypatch):
    from tests import sample_data
    fake = FakeApi(monkeypatch)
    fake.returns.update(sample_data.default_returns())
    return fake


USER_ID = 1


def logged_in_client(is_owner=True, user_id=USER_ID):
    from app import app
    app.config["TESTING"] = True
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user"] = "Dale"
        sess["owner_id"] = user_id
        sess["is_owner"] = is_owner
    return client


@pytest.fixture
def client():
    """Logged in as an owner."""
    return logged_in_client()


@pytest.fixture
def employee():
    """Logged in as an employee (owns nothing)."""
    return logged_in_client(is_owner=False, user_id=2)


def page_text(resp):
    """A response's HTML with entities decoded and whitespace squeezed,
    so tests can look for the sentence a user would read."""
    import html
    import re
    text = re.sub(r"<[^>]+>", " ", resp.get_data(as_text=True))
    return re.sub(r"\s+", " ", html.unescape(text))


# --- The real API, for end-to-end tests -------------------------------------

import importlib.util
import socket
import subprocess
import sys
import time

API_DIR = Path(__file__).resolve().parent.parent.parent / "stock_daddy_api"

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
