import shutil
import sqlite3

import pytest

from app.config import Config
from app.repositories import business_lookup_repository as lookup
from tests.conftest import _REAL_DB




@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    path = tmp_path / "stockdaddy_fresh.db"
    shutil.copyfile(_REAL_DB, path)
    monkeypatch.setattr(Config, "DB_PATH", str(path))
    return path


def _run(path, sql, params=()):
    conn = sqlite3.connect(path)
    cursor = conn.execute(sql, params)
    conn.commit()
    conn.close()
    return cursor.lastrowid


def _second_business_with_item(path):
    
    boss = _run(
        path,
        "INSERT INTO owners (first_name, last_name, email, password_hash) "
        "VALUES ('Bo', 'Ss', 'bo@other.example', 'x')",
    )
    business = _run(path, "INSERT INTO business (name, owner_id) VALUES ('Other Co', ?)", (boss,))
    building = _run(
        path,
        "INSERT INTO building (business_id, state, city, street_address) "
        "VALUES (?, 'KS', 'Hays', '5 Other St')",
        (business,),
    )
    room = _run(path, "INSERT INTO room (building_id, location) VALUES (?, 'Back')", (building,))
    storage = _run(path, "INSERT INTO storage (room_id, storage_type) VALUES (?, 'Shelf')", (room,))
    item = _run(
        path,
        "INSERT INTO item (item_type_id, storage_id, item_name) VALUES (1, ?, 'Other Drill')",
        (storage,),
    )
    return business, building, room, storage, item


def test_seeded_records_belong_to_business_1(fresh_db):
    for kind in ("business", "building", "room", "storage", "item"):
        assert lookup.business_id_for(kind, 1) == 1, kind


def test_records_of_another_business_resolve_to_that_business(fresh_db):
    business, building, room, storage, item = _second_business_with_item(fresh_db)
    assert lookup.business_id_for("business", business) == business
    assert lookup.business_id_for("building", building) == business
    assert lookup.business_id_for("room", room) == business
    assert lookup.business_id_for("storage", storage) == business
    assert lookup.business_id_for("item", item) == business


def test_missing_records_give_none(fresh_db):
    for kind in ("business", "building", "room", "storage", "item"):
        assert lookup.business_id_for(kind, 999999) is None, kind


def test_retired_records_still_resolve(fresh_db):
    _run(fresh_db, "UPDATE item SET retired = CURRENT_TIMESTAMP WHERE item_id = 1")
    assert lookup.business_id_for("item", 1) == 1


def test_item_in_transit_is_found_through_its_last_movement(fresh_db):
    business, _, _, storage, item = _second_business_with_item(fresh_db)
    _run(fresh_db, "UPDATE item SET storage_id = NULL, item_status = 'In Transit' WHERE item_id = ?", (item,))
    _run(
        fresh_db,
        "INSERT INTO item_movement (item_id, from_storage_id, to_storage_id) VALUES (?, ?, NULL)",
        (item, storage),
    )
    assert lookup.business_id_for("item", item) == business

def test_a_status_only_movement_does_not_hide_where_the_item_came_from(fresh_db):
    business, _, _, storage, item = _second_business_with_item(fresh_db)
    _run(fresh_db, "UPDATE item SET storage_id = NULL, item_status = 'In Transit' WHERE item_id = ?", (item,))
    _run(
        fresh_db,
        "INSERT INTO item_movement (item_id, from_storage_id, to_storage_id) VALUES (?, ?, NULL)",
        (item, storage),
    )
    # Later row that only records a status change (no storage unit on it).
    _run(
        fresh_db,
        "INSERT INTO item_movement (item_id, from_status, to_status) VALUES (?, 'In Storage', 'In Transit')",
        (item,),
    )
    assert lookup.business_id_for("item", item) == business

def test_item_with_no_storage_and_no_movement_gives_none(fresh_db):
    item = _run(fresh_db, "INSERT INTO item (item_type_id, item_name) VALUES (1, 'Lost Ladder')")
    assert lookup.business_id_for("item", item) is None


def test_unknown_kind_is_a_programming_error(fresh_db):
    with pytest.raises(KeyError):
        lookup.business_id_for("truck", 1)
        
        
def test_businesses_using_an_item_type_counts_in_transit_items_too(fresh_db):
    assert lookup.businesses_using_item_type(1) == [1]
    assert lookup.businesses_using_item_type(999999) == []

    business, _, _, storage, item = _second_business_with_item(fresh_db)
    assert lookup.businesses_using_item_type(1) == sorted([1, business])

    # Put the other business's item in transit: it still counts for that business.
    _run(fresh_db, "UPDATE item SET storage_id = NULL, item_status = 'In Transit' WHERE item_id = ?", (item,))
    _run(
        fresh_db,
        "INSERT INTO item_movement (item_id, from_storage_id, to_storage_id) VALUES (?, ?, NULL)",
        (item, storage),
    )
    assert lookup.businesses_using_item_type(1) == sorted([1, business])        