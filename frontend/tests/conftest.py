"""
Points the whole test session at a disposable copy of the database instead
of the real stockdaddy.db, the same pattern used in
stock_daddy_api/tests/conftest.py.

db.py reads DB_PATH from an environment variable (falling back to the real
file), so this only has to set that variable before db.py is imported by
anything - which is exactly what conftest.py running first, before test
collection, guarantees.
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

    Tests that write (add rooms, items, ...) use this so they can't change
    the pinned seed-data counts other tests check, whatever order they run in.
    """
    import db

    path = tmp_path / "stockdaddy_fresh.db"
    shutil.copyfile(_REAL_DB, path)
    monkeypatch.setattr(db, "DB_PATH", str(path))
    return path
