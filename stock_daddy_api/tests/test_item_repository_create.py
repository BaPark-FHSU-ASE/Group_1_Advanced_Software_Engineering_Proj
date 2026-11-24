import shutil
import sqlite3

import pytest

from app.config import Config
from app.db.connection import get_connection
from app.models.item import Item
from app.repositories import item_repository
from tests.conftest import _REAL_DB
from tests.route_helpers import first_column, one_value, run_sql


@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    path = tmp_path / "stockdaddy_item_create.db"
    shutil.copyfile(_REAL_DB, path)
    monkeypatch.setattr(Config, "DB_PATH", str(path))
    return path

def test_create_inserts_and_returns_item():
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO item (item_type_id, storage_id, item_name, item_status) VALUES (?, ?, ?, ?)",
            (1, 1, "Test Nail Gun", "In Storage"),
        )
        new_item_id = cursor.lastrowid
        row = conn.execute(
            "SELECT * FROM item WHERE item_id = ?", (new_item_id,)
        ).fetchone()
        item = Item.from_row(row)

        assert item.item_id == new_item_id
        assert item.item_type_id == 1
        assert item.storage_id == 1
        assert item.item_name == "Test Nail Gun"
        assert item.item_status == "In Storage"
    finally:
        conn.rollback()
        conn.close()
        
def test_create_many_adds_each_item_in_storage_with_one_arrival_movement(fresh_db):
    items_before = one_value(fresh_db, "SELECT COUNT(*) FROM item")
    ids = item_repository.create_many(2, 3, ["Compressor A", "Compressor B"])

    assert len(ids) == 2
    assert one_value(fresh_db, "SELECT COUNT(*) FROM item") == items_before + 2
    assert first_column(fresh_db, f"SELECT item_name FROM item WHERE item_id IN ({ids[0]}, {ids[1]}) ORDER BY item_id") == [
        "Compressor A", "Compressor B"]
    for item_id in ids:
        row = sqlite3.connect(fresh_db).execute(
            "SELECT item_type_id, storage_id, item_status FROM item WHERE item_id = ?", (item_id,)
        ).fetchone()
        assert row == (2, 3, "In Storage")
        movements = sqlite3.connect(fresh_db).execute(
            "SELECT from_storage_id, to_storage_id, from_status, to_status "
            "FROM item_movement WHERE item_id = ?", (item_id,)
        ).fetchall()
        assert movements == [(None, 3, None, None)]


def test_create_many_with_no_names_adds_nothing(fresh_db):
    items_before = one_value(fresh_db, "SELECT COUNT(*) FROM item")
    assert item_repository.create_many(1, 1, []) == []
    assert one_value(fresh_db, "SELECT COUNT(*) FROM item") == items_before


def test_create_many_saves_nothing_if_one_item_fails_part_way(fresh_db):
    run_sql(
        fresh_db,
        "CREATE TRIGGER refuse_boom BEFORE INSERT ON item WHEN NEW.item_name = 'boom' "
        "BEGIN SELECT RAISE(ABORT, 'boom'); END",
    )
    items_before = one_value(fresh_db, "SELECT COUNT(*) FROM item")
    movements_before = one_value(fresh_db, "SELECT COUNT(*) FROM item_movement")

    with pytest.raises(sqlite3.DatabaseError):
        item_repository.create_many(1, 1, ["fine", "also fine", "boom"])

    assert one_value(fresh_db, "SELECT COUNT(*) FROM item") == items_before
    assert one_value(fresh_db, "SELECT COUNT(*) FROM item_movement") == movements_before


def test_create_many_refuses_a_storage_unit_that_does_not_exist(fresh_db):
    items_before = one_value(fresh_db, "SELECT COUNT(*) FROM item")
    with pytest.raises(sqlite3.IntegrityError):
        item_repository.create_many(1, 999999, ["ghost"])
    assert one_value(fresh_db, "SELECT COUNT(*) FROM item") == items_before


def test_count_of_type_counts_every_item_of_that_type_retired_or_not(fresh_db):
    expected = one_value(fresh_db, "SELECT COUNT(*) FROM item WHERE item_type_id = 1")
    assert item_repository.count_of_type(1) == expected
    run_sql(fresh_db, "UPDATE item SET retired = CURRENT_TIMESTAMP WHERE item_type_id = 1")
    assert item_repository.count_of_type(1) == expected
    assert item_repository.count_of_type(999999) == 0        