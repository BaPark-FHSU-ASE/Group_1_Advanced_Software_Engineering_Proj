"""
Tests for schema_v7.sql: business_member, plan_run, and the retired-item/
retired-building filtering in v_building_item_type_counts and
v_building_item_type_position.
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


def _scalar(sql, params=()):
    conn = db.get_connection()
    try:
        return conn.execute(sql, params).fetchone()[0]
    finally:
        conn.close()


# --- business_member ---------------------------------------------------

def test_business_member_rejects_unknown_role():
    with pytest.raises(sqlite3.IntegrityError):
        _execute(
            "INSERT INTO business_member (business_id, owner_id, role) VALUES (1, 1, 'manager')"
        )


def test_business_member_accepts_owner_and_employee():
    _execute(
        "INSERT INTO owners (first_name, last_name, email, password_hash) "
        "VALUES ('New', 'Hire', 'newhire@example.com', 'x')"
    )
    new_owner_id = _scalar("SELECT owner_id FROM owners WHERE email = 'newhire@example.com'")
    _execute(
        "INSERT INTO business_member (business_id, owner_id, role) VALUES (1, ?, 'employee')",
        (new_owner_id,),
    )


def test_business_member_rejects_duplicate_membership():
    # owner_id 1 is already a member of business 1 (seed data)
    with pytest.raises(sqlite3.IntegrityError):
        _execute(
            "INSERT INTO business_member (business_id, owner_id, role) VALUES (1, 1, 'employee')"
        )


def test_seed_backfilled_existing_owner_as_owner_role():
    role = _scalar(
        "SELECT role FROM business_member WHERE business_id = 1 AND owner_id = 1"
    )
    assert role == "owner"


# --- plan_run -----------------------------------------------------------

def test_plan_run_rejects_negative_cost():
    with pytest.raises(sqlite3.IntegrityError):
        _execute(
            "INSERT INTO plan_run (business_id, run_by, method, total_cost, baseline_cost, gap, plan_json) "
            "VALUES (1, 1, 'branch_and_bound', -1.0, 100.0, 0.0, '{}')"
        )


def test_plan_run_rejects_gap_out_of_range():
    with pytest.raises(sqlite3.IntegrityError):
        _execute(
            "INSERT INTO plan_run (business_id, run_by, method, total_cost, baseline_cost, gap, plan_json) "
            "VALUES (1, 1, 'branch_and_bound', 100.0, 150.0, 1.5, '{}')"
        )


def test_plan_run_accepts_valid_row():
    _execute(
        "INSERT INTO plan_run (business_id, run_by, method, total_cost, baseline_cost, gap, plan_json) "
        "VALUES (1, 1, 'branch_and_bound', 575.44, 1072.19, 0.0, '{\"trips\": []}')"
    )
    count = _scalar("SELECT COUNT(*) FROM plan_run")
    assert count == 1


# --- retired filtering ---------------------------------------------------

def test_retired_item_excluded_from_counts():
    before = _scalar(
        "SELECT present_qty FROM v_building_item_type_counts "
        "WHERE building_id = 1 AND item_type_id = 1"
    )
    item_id = _scalar(
        "SELECT item_id FROM item WHERE item_name = 'Nail Gun #1'"
    )
    _execute("UPDATE item SET retired = datetime('now') WHERE item_id = ?", (item_id,))
    after = _scalar(
        "SELECT present_qty FROM v_building_item_type_counts "
        "WHERE building_id = 1 AND item_type_id = 1"
    )
    assert after == before - 1


def test_retired_building_excluded_from_position_view():
    before_count = _scalar(
        "SELECT COUNT(*) FROM v_building_item_type_position WHERE building_id = 1"
    )
    assert before_count > 0
    _execute("UPDATE building SET retired = datetime('now') WHERE building_id = 1")
    after_count = _scalar(
        "SELECT COUNT(*) FROM v_building_item_type_position WHERE building_id = 1"
    )
    assert after_count == 0


def test_active_buildings_unaffected_by_another_buildings_retirement():
    _execute("UPDATE building SET retired = datetime('now') WHERE building_id = 1")
    # Building 2 (Salina South) should be untouched
    count = _scalar(
        "SELECT COUNT(*) FROM v_building_item_type_position WHERE building_id = 2"
    )
    assert count > 0
