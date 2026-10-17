"""
Tests for db.get_expired_items() (REQ-23).

Seed items all get date_added = today, so none are expired out of the box.
These tests insert items with a backdated date_added to simulate age.
"""

import pytest

import db

OWNER = 1
OTHER_OWNER = 999999

# item_type 1 = Nail Gun, service_life_days = 730
# item_type 2 = Air Compressor, service_life_days = NULL (no limit)
NAIL_GUN = 1
AIR_COMPRESSOR = 2


@pytest.fixture(autouse=True)
def _isolated(fresh_db):
    """Every test here writes, so each gets its own copy of the database."""


def _add_aged_item(item_type_id, storage_id, age_days, name="Aged Item"):
    conn = db.get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO item (item_type_id, storage_id, item_name, item_status, date_added) "
            "VALUES (?, ?, ?, 'In Storage', datetime('now', ? || ' days'))",
            (item_type_id, storage_id, name, -age_days),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def test_item_past_service_life_is_flagged():
    item_id = _add_aged_item(NAIL_GUN, 1, age_days=800)  # limit is 730
    flagged_ids = [i["id"] for i in db.get_expired_items(OWNER)]
    assert item_id in flagged_ids


def test_item_within_service_life_is_not_flagged():
    item_id = _add_aged_item(NAIL_GUN, 1, age_days=100)  # well under 730
    flagged_ids = [i["id"] for i in db.get_expired_items(OWNER)]
    assert item_id not in flagged_ids


def test_item_type_with_no_limit_is_never_flagged():
    # Air Compressor has service_life_days = NULL - no limit configured
    item_id = _add_aged_item(AIR_COMPRESSOR, 1, age_days=10000)
    flagged_ids = [i["id"] for i in db.get_expired_items(OWNER)]
    assert item_id not in flagged_ids


def test_days_over_is_computed_correctly():
    item_id = _add_aged_item(NAIL_GUN, 1, age_days=735)  # 5 days over 730
    row = next(i for i in db.get_expired_items(OWNER) if i["id"] == item_id)
    assert row["days_over"] == 5


def test_other_owner_items_not_included():
    _add_aged_item(NAIL_GUN, 1, age_days=800)
    flagged = db.get_expired_items(OTHER_OWNER)
    assert flagged == []
