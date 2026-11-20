"""Repository tests for retiring records (block-until-empty rule)."""

import shutil
import sqlite3

import pytest

from app.config import Config
from app.repositories import retire_repository as retire
from tests.conftest import _REAL_DB


@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    path = tmp_path / "stockdaddy_fresh.db"
    shutil.copyfile(_REAL_DB, path)
    monkeypatch.setattr(Config, "DB_PATH", str(path))
    return path


def _one(path, sql, params=()):
    conn = sqlite3.connect(path)
    value = conn.execute(sql, params).fetchone()[0]
    conn.close()
    return value


def _run(path, sql, params=()):
    conn = sqlite3.connect(path)
    cursor = conn.execute(sql, params)
    conn.commit()
    conn.close()
    return cursor.lastrowid


def _retired(path, table, id_column, record_id):
    return _one(path, f"SELECT retired FROM {table} WHERE {id_column} = ?", (record_id,))


def _empty_building(path):
    return _run(
        path,
        "INSERT INTO building (business_id, state, city, street_address) "
        "VALUES (1, 'KS', 'Hays', '1 Empty St')",
    )


def _busy_storage(path):
    """A storage unit that has active items in it."""
    return _one(
        path,
        "SELECT storage_id FROM item WHERE storage_id IS NOT NULL "
        "GROUP BY storage_id ORDER BY COUNT(*) DESC LIMIT 1",
    )


# ---- items (nothing inside an item) ---------------------------------------

def test_retire_an_item(fresh_db):
    assert retire.retire("item", 1) == (retire.RETIRED, {})
    assert _retired(fresh_db, "item", "item_id", 1) is not None


def test_retiring_twice_says_already_retired(fresh_db):
    retire.retire("item", 1)
    first_stamp = _retired(fresh_db, "item", "item_id", 1)
    assert retire.retire("item", 1) == (retire.ALREADY_RETIRED, {})
    assert _retired(fresh_db, "item", "item_id", 1) == first_stamp


def test_retire_unknown_record_says_not_found(fresh_db):
    for kind in ("business", "building", "room", "storage", "item"):
        assert retire.retire(kind, 999999) == (retire.NOT_FOUND, {})


def test_unknown_kind_is_a_programming_error(fresh_db):
    with pytest.raises(KeyError):
        retire.retire("truck", 1)


# ---- block until empty ----------------------------------------------------

def test_storage_with_items_is_blocked_and_counts_them(fresh_db):
    storage_id = _busy_storage(fresh_db)
    expected = _one(
        fresh_db,
        "SELECT COUNT(*) FROM item WHERE storage_id = ? AND retired IS NULL",
        (storage_id,),
    )
    assert expected > 0
    assert retire.retire("storage", storage_id) == (retire.NOT_EMPTY, {"items": expected})
    assert _retired(fresh_db, "storage", "storage_id", storage_id) is None


def test_room_building_and_business_report_everything_inside(fresh_db):
    room_inside = retire.still_inside("room", 1)
    assert set(room_inside) <= {"storage_units", "items"} and room_inside

    building_inside = retire.still_inside("building", 1)
    assert building_inside["rooms"] >= 1
    assert building_inside["items"] >= room_inside.get("items", 0)

    business_inside = retire.still_inside("business", 1)
    assert business_inside["buildings"] == _one(
        fresh_db, "SELECT COUNT(*) FROM building WHERE business_id = 1 AND retired IS NULL"
    )
    assert business_inside["items"] == _one(
        fresh_db, "SELECT COUNT(*) FROM item WHERE retired IS NULL AND storage_id IS NOT NULL"
    )


def test_blocked_retire_changes_nothing(fresh_db):
    outcome, inside = retire.retire("building", 1)
    assert outcome == retire.NOT_EMPTY and inside
    assert _retired(fresh_db, "building", "building_id", 1) is None


def test_retired_items_stop_counting(fresh_db):
    storage_id = _busy_storage(fresh_db)
    before = retire.still_inside("storage", storage_id)["items"]
    one_item = _one(fresh_db, "SELECT item_id FROM item WHERE storage_id = ? LIMIT 1", (storage_id,))
    retire.retire("item", one_item)
    after = retire.still_inside("storage", storage_id).get("items", 0)
    assert after == before - 1


def test_an_empty_record_retires_straight_away(fresh_db):
    building_id = _empty_building(fresh_db)
    assert retire.still_inside("building", building_id) == {}
    assert retire.retire("building", building_id) == (retire.RETIRED, {})
    assert _retired(fresh_db, "building", "building_id", building_id) is not None


def test_retiring_works_bottom_up_all_the_way_to_the_business(fresh_db):
    for item_id in [r[0] for r in sqlite3.connect(fresh_db).execute("SELECT item_id FROM item")]:
        assert retire.retire("item", item_id)[0] == retire.RETIRED
    for kind, table, column in (
        ("storage", "storage", "storage_id"),
        ("room", "room", "room_id"),
        ("building", "building", "building_id"),
    ):
        ids = [r[0] for r in sqlite3.connect(fresh_db).execute(f"SELECT {column} FROM {table}")]
        for record_id in ids:
            assert retire.retire(kind, record_id)[0] == retire.RETIRED, (kind, record_id)
    assert retire.still_inside("business", 1) == {}
    assert retire.retire("business", 1) == (retire.RETIRED, {})


def test_active_items_in_a_retired_storage_unit_still_block_the_room(fresh_db):
    """Retired parent, active child: the child still counts as inside."""
    storage_id = _busy_storage(fresh_db)
    room_id = _one(fresh_db, "SELECT room_id FROM storage WHERE storage_id = ?", (storage_id,))
    _run(fresh_db, "UPDATE storage SET retired = CURRENT_TIMESTAMP WHERE storage_id = ?", (storage_id,))
    assert retire.still_inside("room", room_id)["items"] > 0

def test_is_retired_tells_active_retired_and_missing_apart(fresh_db):
    assert retire.is_retired("item", 1) is False
    retire.retire("item", 1)
    assert retire.is_retired("item", 1) is True
    assert retire.is_retired("item", 999999) is None
