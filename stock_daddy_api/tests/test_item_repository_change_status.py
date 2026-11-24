import shutil
import sqlite3

import pytest

from app.config import Config
from app.repositories import item_repository
from tests.conftest import _REAL_DB
from tests.route_helpers import one_value, run_sql

# Seed: item 1 is In Storage in storage unit 1; item 92 is In Transit with no storage unit.


@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    path = tmp_path / "stockdaddy_item_status.db"
    shutil.copyfile(_REAL_DB, path)
    monkeypatch.setattr(Config, "DB_PATH", str(path))
    return path


def _rows(path, sql, params=()):
    conn = sqlite3.connect(path)
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return rows


def _last_movement(path, item_id):
    return _rows(
        path,
        "SELECT from_storage_id, to_storage_id, from_status, to_status FROM item_movement "
        "WHERE item_id = ? ORDER BY item_movement_id DESC LIMIT 1", (item_id,),
    )[0]


def test_a_status_swap_in_place_logs_only_the_statuses(fresh_db):
    assert item_repository.change_status(1, "In Storage", 1, "In Use", 1) is True
    assert _rows(fresh_db, "SELECT item_status, storage_id FROM item WHERE item_id = 1") == [("In Use", 1)]
    assert _last_movement(fresh_db, 1) == (None, None, "In Storage", "In Use")


def test_leaving_a_storage_unit_logs_where_it_left_from(fresh_db):
    assert item_repository.change_status(1, "In Storage", 1, "In Transit", None) is True
    assert _rows(fresh_db, "SELECT item_status, storage_id FROM item WHERE item_id = 1") == [("In Transit", None)]
    assert _last_movement(fresh_db, 1) == (1, None, "In Storage", "In Transit")


def test_arriving_logs_where_it_arrived(fresh_db):
    assert item_repository.change_status(92, "In Transit", None, "In Storage", 4) is True
    assert _rows(fresh_db, "SELECT item_status, storage_id FROM item WHERE item_id = 92") == [("In Storage", 4)]
    assert _last_movement(fresh_db, 92) == (None, 4, "In Transit", "In Storage")


def test_a_stale_old_status_saves_nothing(fresh_db):
    movements = one_value(fresh_db, "SELECT COUNT(*) FROM item_movement")
    assert item_repository.change_status(1, "In Use", 1, "In Transit", None) is False
    assert _rows(fresh_db, "SELECT item_status, storage_id FROM item WHERE item_id = 1") == [("In Storage", 1)]
    assert one_value(fresh_db, "SELECT COUNT(*) FROM item_movement") == movements


def test_if_the_movement_row_fails_the_item_is_left_alone(fresh_db):
    run_sql(
        fresh_db,
        "CREATE TRIGGER refuse_move BEFORE INSERT ON item_movement WHEN NEW.to_status = 'In Use' "
        "BEGIN SELECT RAISE(ABORT, 'refused'); END",
    )
    movements = one_value(fresh_db, "SELECT COUNT(*) FROM item_movement")
    with pytest.raises(sqlite3.DatabaseError):
        item_repository.change_status(1, "In Storage", 1, "In Use", 1)
    assert _rows(fresh_db, "SELECT item_status FROM item WHERE item_id = 1") == [("In Storage",)]
    assert one_value(fresh_db, "SELECT COUNT(*) FROM item_movement") == movements