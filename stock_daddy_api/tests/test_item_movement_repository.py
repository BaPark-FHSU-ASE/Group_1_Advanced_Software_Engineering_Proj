import shutil

import pytest

from app.config import Config
from app.models.item_movement import ItemMovement
from app.repositories import item_movement_repository as movements
from tests.conftest import _REAL_DB
from tests.route_helpers import add_person, one_value, run_sql

# Seed: 94 movement rows for business 1's items (Dale owner_id 1, Jess owner_id 2).


@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    path = tmp_path / "stockdaddy_item_movement.db"
    shutil.copyfile(_REAL_DB, path)
    monkeypatch.setattr(Config, "DB_PATH", str(path))
    return path


def test_search_returns_every_visible_movement_newest_first(fresh_db):
    found = movements.search(1)
    assert len(found) == 94
    keys = [(m.moved_at, m.item_movement_id) for m in found]
    assert keys == sorted(keys, reverse=True)
    assert len(movements.search(2)) == 94
    assert movements.search(add_person(fresh_db)) == []
    assert movements.search(999999) == []


def test_search_leaves_out_retired_items(fresh_db):
    run_sql(fresh_db, "UPDATE item SET retired = CURRENT_TIMESTAMP WHERE item_id = 92")
    assert 92 not in {m.item_id for m in movements.search(1)}
    assert len(movements.search(1)) == 93


def test_search_fills_in_the_places_and_the_building(fresh_db):
    by_id = {m.item_movement_id: m for m in movements.search(1)}
    left = by_id[93]
    assert (left.from_place, left.to_place, left.building) == ("Salina / Salina North main storage / Locker", None, "Salina")
    status_only = by_id[94]
    assert (status_only.from_place, status_only.to_place, status_only.building) == (None, None, "Salina")
    assert (status_only.from_status, status_only.to_status) == ("In Storage", "In Use")


def test_a_status_only_row_belongs_to_the_building_the_item_was_in_then(fresh_db):
    # Item 4's status-only row (94) happened while it sat in building 1; moving it later must not change that.
    run_sql(fresh_db, "UPDATE item SET storage_id = 5 WHERE item_id = 4")
    run_sql(fresh_db, "INSERT INTO item_movement (item_id, from_storage_id, to_storage_id, moved_at) VALUES (4, 1, 5, '2026-12-01 10:00:00')")
    row = [m for m in movements.search(1, item_id=4) if m.item_movement_id == 94][0]
    assert row.building == "Salina"


def test_each_filter_narrows_the_search(fresh_db):
    assert {m.item_id for m in movements.search(1, item_id=92)} == {92}
    assert {m.item_type for m in movements.search(1, item_type_id=2)} == {"Air Compressor"}
    assert [m.item_movement_id for m in movements.search(1, status="In Use")] == [94]
    assert [m.item_movement_id for m in movements.search(1, date_from="2026-11-01", date_to="2026-11-01")] == [94]
    assert all(m.building == "Abilene" for m in movements.search(1, building_id=3))
    assert movements.search(1, building_id=3)


def test_the_name_search_ignores_capitals_and_treats_percent_and_underscore_as_plain_characters(fresh_db):
    assert movements.search(1, q="nail gun #4")
    assert movements.search(1, q="%") == []
    assert movements.search(1, q="_") == []


def test_to_dict_uses_the_history_wording():
    full = ItemMovement(7, "2026-11-02 10:00:00", "In Storage", "In Transit", 2, "Nail Gun #2", "Nail Gun",
                        "Hays", "Hays / Tool Room / Locker", None)
    assert full.to_dict() == {
        "movement_id": 7, "date": "2026-11-02", "item_id": 2, "item_name": "Nail Gun #2", "item_type": "Nail Gun",
        "building": "Hays", "from": "Hays / Tool Room / Locker", "to": "—", "status_change": "In Storage → In Transit",
    }
    plain = ItemMovement(1, None, None, None, 1, None, "Hard Hat", None, None, None).to_dict()
    assert (plain["date"], plain["building"], plain["from"], plain["to"], plain["status_change"]) == ("—", "—", "—", "—", None)
    assert ItemMovement(2, "2026-11-02 10:00:00", None, "In Use", 1, "x", "y", "z", None, None).to_dict()["status_change"] == "— → In Use"
