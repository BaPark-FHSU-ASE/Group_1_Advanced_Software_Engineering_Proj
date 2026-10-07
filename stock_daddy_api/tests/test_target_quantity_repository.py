"""Repository tests for target quantities (REQ-15)."""

import shutil
import sqlite3

import pytest

from app.config import Config
from app.repositories import target_quantity_repository
from tests.conftest import _REAL_DB


@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    """A private database copy per test, so writes can't leak between tests."""
    path = tmp_path / "stockdaddy_fresh.db"
    shutil.copyfile(_REAL_DB, path)
    monkeypatch.setattr(Config, "DB_PATH", str(path))
    return path


def _row_count(path, building_id, item_type_id):
    conn = sqlite3.connect(path)
    count = conn.execute(
        "SELECT COUNT(*) FROM target_quantity WHERE building_id = ? AND item_type_id = ?",
        (building_id, item_type_id),
    ).fetchone()[0]
    conn.close()
    return count


def _add_item_type(path, name):
    """Seed data has a target for every item type in every building, so a
    brand-new target needs a brand-new item type."""
    conn = sqlite3.connect(path)
    cursor = conn.execute("INSERT INTO item_type (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()
    return cursor.lastrowid


def test_get_all_returns_seeded_targets(fresh_db):
    assert len(target_quantity_repository.get_all()) == 30


def test_get_all_filters_by_building(fresh_db):
    targets = target_quantity_repository.get_all(building_id=1)
    assert len(targets) == 6
    assert all(t.building_id == 1 for t in targets)


def test_get_by_id_returns_target(fresh_db):
    target = target_quantity_repository.get_by_id(1)
    assert target.to_dict() == {
        "target_quantity_id": 1,
        "building_id": 1,
        "item_type_id": 1,
        "target_qty": 3,
    }


def test_get_by_id_missing_returns_none(fresh_db):
    assert target_quantity_repository.get_by_id(999999) is None


def test_set_target_updates_existing_row_instead_of_duplicating(fresh_db):
    # Seed data already has a target of 3 for building 1 / Nail Gun (type 1).
    target, created = target_quantity_repository.set_target(1, 1, 7)
    assert created is False
    assert target.target_qty == 7
    assert target.target_quantity_id == 1
    assert _row_count(fresh_db, 1, 1) == 1


def test_set_target_creates_new_row(fresh_db):
    item_type_id = _add_item_type(fresh_db, "Test Drill")
    target, created = target_quantity_repository.set_target(1, item_type_id, 2)
    assert created is True
    assert target.target_qty == 2
    assert _row_count(fresh_db, 1, item_type_id) == 1


def test_set_target_zero_is_allowed(fresh_db):
    target, _ = target_quantity_repository.set_target(1, 1, 0)
    assert target.target_qty == 0


def test_building_owned_by(fresh_db):
    assert target_quantity_repository.building_owned_by(1, 1) is True
    assert target_quantity_repository.building_owned_by(1, 999999) is False
    assert target_quantity_repository.building_owned_by(999999, 1) is False


def test_item_type_exists(fresh_db):
    assert target_quantity_repository.item_type_exists(1) is True
    assert target_quantity_repository.item_type_exists(999999) is False


def test_delete(fresh_db):
    assert target_quantity_repository.delete(1) is True
    assert target_quantity_repository.get_by_id(1) is None
    assert target_quantity_repository.delete(1) is False
