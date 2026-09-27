"""
Points the whole test session at a disposable copy of the database instead
of the real frontend/stockdaddy.db.

Why this is needed: several repository functions (owner_repository.delete,
.create, .update, etc.) open their own connection and commit internally.
A test wrapping its own connection in conn.rollback() can't undo that -
the repository's commit already happened on a separate connection. Net row
counts come out right (create-then-delete tests do clean up the rows), but
each create still permanently advances SQLite's AUTOINCREMENT counter,
since AUTOINCREMENT never reuses an id even after the row is deleted. Run
the suite enough times against the real file and the shared, git-committed
seed database silently drifts (verified: owners/business sqlite_sequence
values move up by 1 in the working tree after every plain `pytest` run.
`git status` will show frontend/stockdaddy.db as modified with a binary
diff nobody can read).

Config.DB_PATH already reads from an environment variable (see
app/config.py), so no code elsewhere needs to change - this just has to run
before anything imports app.config, which is why it lives in conftest.py
at module level: pytest loads conftest.py before collecting/importing any
test module.
"""

import os
import shutil
import tempfile
from pathlib import Path

_REAL_DB = Path(__file__).resolve().parent.parent.parent / "frontend" / "stockdaddy.db"

_tmp_dir = tempfile.mkdtemp(prefix="stockdaddy_test_")
_tmp_db_path = Path(_tmp_dir) / "stockdaddy_test.db"
shutil.copyfile(_REAL_DB, _tmp_db_path)

# Must happen before any test module (or anything it imports) pulls in
# app.config - Config.DB_PATH is read once, at class-definition time.
os.environ["DB_PATH"] = str(_tmp_db_path)


def pytest_sessionfinish(session, exitstatus):
    shutil.rmtree(_tmp_dir, ignore_errors=True)
