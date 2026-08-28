# Database Setup

**Engine: SQLite** (switched from MySQL 8/26 — team decision: no server to
install, `sqlite3` ships with Python, and cloning the repo gives everyone a
working database immediately since the `.db` file is checked in).

## The easy path: it's already built

`frontend/stockdaddy.db` is committed to the repo. Clone the project,
`cd frontend`, `pip install -r requirements.txt`, `python app.py` — there is
no separate database setup step. See `frontend/README.md` for the full run
instructions.

You only need anything below this line if you're changing the schema or
seed data yourself.

## Rebuilding the database

If you edit `schema_v5.sql` or `seed_data_v5.sql`, rebuild the `.db` file and
commit it alongside your change — the app reads that file directly, so a
schema change nobody rebuilds into it has no effect for anyone else:

```bash
python Schema_versions/build_db.py
```

This drops and recreates `frontend/stockdaddy.db` from scratch. No arguments,
no server, no credentials — it's a plain Python script using the standard
library's `sqlite3` module.

## Poking at the database directly

The `sqlite3` CLI ships with Python (`python -m sqlite3` if you don't have
the standalone binary) — no separate install:

```bash
sqlite3 frontend/stockdaddy.db
sqlite> SELECT * FROM v_building_item_type_position LIMIT 5;
sqlite> .quit
```

Or point any SQLite-capable GUI (DB Browser for SQLite, TablePlus, the
SQLite extension in VS Code, etc.) at the same file.

## Verify

Run this after building, to confirm the schema and seed data are behaving:

```bash
sqlite3 frontend/stockdaddy.db < Schema_versions/seed_data_v5.sql
```

(Re-running seed_data_v5.sql against an already-seeded DB will fail on the
UNIQUE constraints — that's expected. If you actually want a fresh copy,
use `build_db.py`, which starts from an empty file.)

The seed data creates a test login (see `frontend/README.md` for the
credentials) so you can log into the frontend without registering a new
account first.

## Files

- `schema_v5.sql` — current schema (table/view/index definitions only, no
  data), SQLite dialect. Adds `owners.email` and `owners.password_hash` so
  the frontend can support real registration/login instead of the old
  hardcoded stub. Passwords are hashed (werkzeug, scrypt-based) in the
  frontend before ever reaching the DB — this table should never contain a
  plaintext password. See the file's header for the full MySQL→SQLite
  porting notes (generated columns, FK enforcement, DECIMAL precision).
- `seed_data_v5.sql` — same five-site roofing scenario as v4, ported to
  SQLite, with the owner insert updated to include a real email/password
  hash for local testing.
- `build_db.py` — rebuilds `frontend/stockdaddy.db` from the two files
  above. Run this after any schema/seed change.
- `schema_v4.sql` / `seed_data_v4.sql` and earlier — MySQL-dialect,
  superseded by the engine switch. Kept for history; not runnable against
  SQLite without the same porting `schema_v5.sql` went through. See each
  file's header comment for what changed at that step.
