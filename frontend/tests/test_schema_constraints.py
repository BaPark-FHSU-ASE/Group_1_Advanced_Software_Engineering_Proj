"""
Tests for the 9 CHECK constraints in schema_v6.sql.

Each constraint gets one test that tries to insert the exact value it
exists to reject, and confirms sqlite3 raises IntegrityError, not just a
reading of the DDL. Where a constraint allows NULL (the "not configured"
convention), there's a second test confirming NULL is accepted.
"""

import sqlite3

import pytest

import db

OWNER = 1


@pytest.fixture(autouse=True)
def _isolated(fresh_db):
    """Every test here writes, so each gets its own copy of the database."""


def _execute(sql, params=()):
    conn = db.get_connection()
    try:
        conn.execute(sql, params)
        conn.commit()
    finally:
        conn.close()


# --- item_type ---------------------------------------------------------

def test_replacement_cost_rejects_zero_and_negative():
    with pytest.raises(sqlite3.IntegrityError):
        _execute(
            "INSERT INTO item_type (name, replacement_cost) VALUES (?, ?)",
            ("Bad Type A", 0),
        )
    with pytest.raises(sqlite3.IntegrityError):
        _execute(
            "INSERT INTO item_type (name, replacement_cost) VALUES (?, ?)",
            ("Bad Type B", -5.00),
        )


def test_replacement_cost_allows_null():
    _execute(
        "INSERT INTO item_type (name, replacement_cost) VALUES (?, NULL)",
        ("Unpriced Type",),
    )


def test_service_life_rejects_zero_and_negative():
    with pytest.raises(sqlite3.IntegrityError):
        _execute(
            "INSERT INTO item_type (name, service_life_days) VALUES (?, ?)",
            ("Bad Type C", 0),
        )
    with pytest.raises(sqlite3.IntegrityError):
        _execute(
            "INSERT INTO item_type (name, service_life_days) VALUES (?, ?)",
            ("Bad Type D", -30),
        )


def test_service_life_allows_null():
    _execute(
        "INSERT INTO item_type (name, service_life_days) VALUES (?, NULL)",
        ("No Limit Type",),
    )


# --- item ----------------------------------------------------------------

def test_item_status_rejects_unlisted_value():
    with pytest.raises(sqlite3.IntegrityError):
        _execute(
            "INSERT INTO item (item_type_id, item_name, item_status) "
            "VALUES (1, 'Bad Item', 'Lost')",
        )


# --- target_quantity -------------------------------------------------------

def test_target_qty_rejects_negative():
    with pytest.raises(sqlite3.IntegrityError):
        _execute(
            "INSERT INTO target_quantity (building_id, item_type_id, target_qty) "
            "VALUES (1, 1, -1)",
        )


# --- item_movement ---------------------------------------------------------

def test_movement_rejects_bad_status_value():
    with pytest.raises(sqlite3.IntegrityError):
        _execute(
            "INSERT INTO item_movement (item_id, from_status, to_status) "
            "VALUES (1, 'In Storage', 'Missing')",
        )


def test_movement_rejects_all_null_row():
    with pytest.raises(sqlite3.IntegrityError):
        _execute(
            "INSERT INTO item_movement (item_id) VALUES (1)",
        )


def test_movement_accepts_status_only_row():
    _execute(
        "INSERT INTO item_movement (item_id, from_status, to_status) "
        "VALUES (1, 'In Storage', 'In Use')",
    )


def test_movement_accepts_location_only_row():
    _execute(
        "INSERT INTO item_movement (item_id, from_storage_id, to_storage_id) "
        "VALUES (1, 1, 2)",
    )


# --- building_route ---------------------------------------------------------

def test_route_rejects_same_building_both_ends():
    with pytest.raises(sqlite3.IntegrityError):
        _execute(
            "INSERT INTO building_route "
            "(from_building_id, to_building_id, distance_miles, "
            " fixed_dispatch_cost, cost_per_unit_mile) "
            "VALUES (1, 1, 10.0, 50.0, 0.10)",
        )


def test_route_rejects_zero_dispatch_cost():
    with pytest.raises(sqlite3.IntegrityError):
        _execute(
            "INSERT INTO building_route "
            "(from_building_id, to_building_id, distance_miles, "
            " fixed_dispatch_cost, cost_per_unit_mile) "
            "VALUES (1, 2, 10.0, 0, 0.10)",
        )


def test_route_rejects_negative_rate_or_distance():
    with pytest.raises(sqlite3.IntegrityError):
        _execute(
            "INSERT INTO building_route "
            "(from_building_id, to_building_id, distance_miles, "
            " fixed_dispatch_cost, cost_per_unit_mile) "
            "VALUES (1, 2, -1.0, 50.0, 0.10)",
        )
    with pytest.raises(sqlite3.IntegrityError):
        _execute(
            "INSERT INTO building_route "
            "(from_building_id, to_building_id, distance_miles, "
            " fixed_dispatch_cost, cost_per_unit_mile) "
            "VALUES (1, 2, 10.0, 50.0, -0.01)",
        )
