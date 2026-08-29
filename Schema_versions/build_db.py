#!/usr/bin/env python3
"""
Build (or rebuild) the SQLite database file from schema_v5.sql + seed_data_v5.sql.

Run this after any schema/seed change, or if you deleted the .db file and
want it back:

    python Schema_versions/build_db.py

Writes to frontend/stockdaddy.db (overwriting it if it exists) — that's the
file the frontend actually reads at runtime, and it's checked into the repo
so cloning the project gives everyone a working database with zero setup.
If you change schema_v5.sql or seed_data_v5.sql, re-run this and commit the
resulting .db file alongside your change.
"""

import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCHEMA_FILE = HERE / "schema_v5.sql"
SEED_FILE = HERE / "seed_data_v5.sql"
DB_FILE = HERE.parent / "frontend" / "stockdaddy.db"


def main():
    if DB_FILE.exists():
        DB_FILE.unlink()

    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON;")

    conn.executescript(SCHEMA_FILE.read_text(encoding="utf-8"))
    print(f"Schema applied from {SCHEMA_FILE.name}")

    conn.executescript(SEED_FILE.read_text(encoding="utf-8"))
    print(f"Seed data applied from {SEED_FILE.name}")

    conn.commit()
    conn.close()
    print(f"Built {DB_FILE}")


if __name__ == "__main__":
    sys.exit(main())
