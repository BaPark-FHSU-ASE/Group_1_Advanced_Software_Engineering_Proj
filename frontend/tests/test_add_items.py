"""
Tests for db.add_items() and the dropdown helpers behind the Add Items form.

Owner 1 is the seeded account. Storage 1 is a locker in Salina North
(building 1); item type 1 is Nail Gun.
"""

import sqlite3

import pytest

import db

@pytest.fixture(autouse=True)
def _isolated(fresh_db):
    """Every test here writes, so each gets its own copy of the database."""


OWNER = 1
OTHER_OWNER = 999999


def _movements_for(item_id):
    conn = sqlite3.connect(db.DB_PATH)
    try:
        return conn.execute(
            "SELECT from_storage_id, to_storage_id FROM item_movement WHERE item_id = ?",
            (item_id,),
        ).fetchall()
    finally:
        conn.close()


def test_add_one_item_with_name():
    [item_id] = db.add_items(OWNER, 1, 1, 1, "Test Nailer")
    item = db.get_item_detail(OWNER, item_id)
    assert item["name"] == "Test Nailer"
    assert item["type"] == "Nail Gun"
    assert item["status"] == "In Storage"


def test_add_several_creates_one_record_each():
    # REQ-14: several of one type in a single action, one record per item
    ids = db.add_items(OWNER, 1, 2, 3, "Compressor")
    assert len(ids) == 3
    names = [db.get_item_detail(OWNER, i)["name"] for i in ids]
    assert names == ["Compressor #1", "Compressor #2", "Compressor #3"]


def test_blank_name_is_numbered_from_existing_items():
    ids = db.add_items(OWNER, 1, 3, 2)
    names = [db.get_item_detail(OWNER, i)["name"] for i in ids]
    assert all(n.startswith("Extension Ladder #") for n in names)
    assert names[0] != names[1]


def test_each_new_item_gets_an_arrival_movement():
    # REQ-12: the item's history starts with where it arrived
    [item_id] = db.add_items(OWNER, 1, 1, 1)
    assert _movements_for(item_id) == [(None, 1)]


def test_rejects_storage_not_owned():
    with pytest.raises(db.NotFoundOrNotOwned):
        db.add_items(OTHER_OWNER, 1, 1, 1)


def test_rejects_unknown_item_type():
    with pytest.raises(db.NotFoundOrNotOwned):
        db.add_items(OWNER, 1, 999999, 1)


@pytest.mark.parametrize("qty", [0, -1, db.MAX_ITEMS_PER_ADD + 1])
def test_rejects_bad_quantity(qty):
    with pytest.raises(ValueError):
        db.add_items(OWNER, 1, 1, qty)


def test_storage_choices_only_include_owners_storage():
    assert len(db.get_storage_choices(OWNER)) > 0
    assert db.get_storage_choices(OTHER_OWNER) == []
