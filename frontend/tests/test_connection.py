"""
Tests for db.get_connection().
"""

import db


def test_get_connection_returns_working_connection():
    conn = db.get_connection()
    result = conn.execute("SELECT 1").fetchone()
    assert result[0] == 1
    conn.close()


def test_get_connection_reads_seeded_owner():
    conn = db.get_connection()
    row = conn.execute("SELECT first_name, last_name, email FROM owners").fetchone()
    assert row["first_name"] == "Dale"
    assert row["last_name"] == "Renner"
    assert row["email"] == "dale@prairieroofing.example"
    conn.close()


def test_foreign_keys_are_enforced():
    conn = db.get_connection()
    result = conn.execute("PRAGMA foreign_keys").fetchone()
    assert result[0] == 1
    conn.close()
