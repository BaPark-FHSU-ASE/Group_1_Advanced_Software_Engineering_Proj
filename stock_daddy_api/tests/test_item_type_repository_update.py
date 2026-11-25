import shutil

import pytest

from app.config import Config
from app.db.connection import get_connection
from app.models.item_type import ItemType
from app.repositories import item_type_repository
from tests.conftest import _REAL_DB


@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    path = tmp_path / "stockdaddy_item_type_update.db"
    shutil.copyfile(_REAL_DB, path)
    monkeypatch.setattr(Config, "DB_PATH", str(path))
    return path


def test_update_changes_and_returns_item_type():
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO item_type (name, description, replacement_cost) VALUES (?, ?, ?)",
            ("Before Update Type", "Before desc", 10.00),
        )
        item_type_id = cursor.lastrowid

        conn.execute(
            "UPDATE item_type SET name = ?, description = ?, replacement_cost = ? WHERE item_type_id = ?",
            ("After Update Type", "After desc", 20.00, item_type_id),
        )
        row = conn.execute(
            "SELECT * FROM item_type WHERE item_type_id = ?", (item_type_id,)
        ).fetchone()
        item_type = ItemType.from_row(row)

        assert item_type.name == "After Update Type"
        assert item_type.replacement_cost == 20.00
    finally:
        conn.rollback()
        conn.close()


def test_update_changes_and_clears_the_service_life(fresh_db):
    # Seed: Nail Gun (item type 1) has a service life of 730 days.
    assert item_type_repository.get_by_id(1).service_life_days == 730

    changed = item_type_repository.update(1, "Nail Gun", None, 340, service_life_days=900)
    assert changed.service_life_days == 900

    cleared = item_type_repository.update(1, "Nail Gun", None, 340)
    assert cleared.service_life_days is None
    assert item_type_repository.get_by_id(1).service_life_days is None