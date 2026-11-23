"""Opens the test copy of the database for the schema tests.

The frontend itself no longer touches the database (everything goes
through the API), but test_schema_*.py and test_connection.py check the
schema and seed data directly, so they open it here. conftest.py points
DB_PATH at a disposable copy before any test runs.
"""

import os
import sqlite3

DB_PATH = os.environ["DB_PATH"]


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    # SQLite only enforces FOREIGN KEY constraints when each connection
    # turns them on.
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn
