"""
Tests for app/db/connection.py.
"""

from app.db.connection import get_connection


def test_get_connection_returns_working_connection():
    conn = get_connection()

    result = conn.execute("SELECT 1").fetchone()

    assert result[0] == 1
    conn.close()


def test_get_connection_reads_seeded_owner():
    conn = get_connection()

    row = conn.execute("SELECT first_name, last_name FROM owners").fetchone()

    assert row["first_name"] == "Dale"
    assert row["last_name"] == "Renner"
    conn.close()


def test_foreign_keys_are_enforced():
    conn = get_connection()

    result = conn.execute("PRAGMA foreign_keys").fetchone()

    assert result[0] == 1
    conn.close()