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
