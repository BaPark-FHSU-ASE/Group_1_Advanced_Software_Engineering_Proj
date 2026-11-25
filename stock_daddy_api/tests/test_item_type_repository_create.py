import shutil

import pytest

from app.config import Config
from app.db.connection import get_connection
from app.models.item_type import ItemType
from app.repositories import item_type_repository
from tests.conftest import _REAL_DB


@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    path = tmp_path / "stockdaddy_item_type_create.db"
    shutil.copyfile(_REAL_DB, path)
    monkeypatch.setattr(Config, "DB_PATH", str(path))
    return path


def test_create_inserts_and_returns_item_type():
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO item_type (name, description, replacement_cost) VALUES (?, ?, ?)",
            ("Test Type", "A test item type", 50.00),
        )
        new_item_type_id = cursor.lastrowid
        row = conn.execute(
            "SELECT * FROM item_type WHERE item_type_id = ?", (new_item_type_id,)
        ).fetchone()
        item_type = ItemType.from_row(row)

        assert item_type.item_type_id == new_item_type_id
        assert item_type.name == "Test Type"
        assert item_type.description == "A test item type"
        assert item_type.replacement_cost == 50.00
    finally:
        conn.rollback()
        conn.close()


def test_create_saves_the_service_life_in_days(fresh_db):
    item_type = item_type_repository.create("Long Lasting", "Lasts", 10.0, service_life_days=365)
    assert item_type.service_life_days == 365
    assert item_type_repository.get_by_id(item_type.item_type_id).service_life_days == 365


def test_create_without_a_service_life_means_no_limit(fresh_db):
    item_type = item_type_repository.create("No Limit", None, None)
    assert item_type.service_life_days is None
    assert item_type.to_dict()["service_life_days"] is None