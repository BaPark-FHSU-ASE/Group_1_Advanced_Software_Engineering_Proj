"""Route tests for /target_quantities (REQ-15, NF-REQ-12)."""

import importlib.util
import shutil
import sqlite3
from pathlib import Path

import pytest

from app.config import Config
from tests.conftest import _REAL_DB

# stock_daddy_api/app.py sits next to the app/ package, so load it by path.
_spec = importlib.util.spec_from_file_location(
    "stock_daddy_api_main", Path(__file__).resolve().parent.parent / "app.py"
)
_main = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_main)

OWNER = 1
OTHER_OWNER = 999999


@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    path = tmp_path / "stockdaddy_fresh.db"
    shutil.copyfile(_REAL_DB, path)
    monkeypatch.setattr(Config, "DB_PATH", str(path))
    return path


@pytest.fixture
def client(fresh_db):
    return _main.app.test_client()


def test_list_targets(client):
    response = client.get("/target_quantities")
    assert response.status_code == 200
    assert len(response.get_json()) == 30


def test_list_targets_for_one_building(client):
    rows = client.get("/target_quantities?building_id=2").get_json()
    assert len(rows) == 6
    assert {r["building_id"] for r in rows} == {2}


def test_get_one_and_missing(client):
    assert client.get("/target_quantities/1").get_json()["target_qty"] == 3
    assert client.get("/target_quantities/999999").status_code == 404


def test_put_updates_existing_target(client, fresh_db):
    response = client.put("/target_quantities/1/1", json={"owner_id": OWNER, "target_qty": 9})
    assert response.status_code == 200
    assert response.get_json()["target_qty"] == 9
    conn = sqlite3.connect(fresh_db)
    rows = conn.execute(
        "SELECT target_qty FROM target_quantity WHERE building_id = 1 AND item_type_id = 1"
    ).fetchall()
    conn.close()
    assert rows == [(9,)]


def test_put_creates_new_target(client, fresh_db):
    conn = sqlite3.connect(fresh_db)
    item_type_id = conn.execute("INSERT INTO item_type (name) VALUES ('Test Drill')").lastrowid
    conn.commit()
    conn.close()
    response = client.put(
        f"/target_quantities/1/{item_type_id}", json={"owner_id": OWNER, "target_qty": 2}
    )
    assert response.status_code == 201


def test_put_rejects_other_owners_building(client):
    response = client.put("/target_quantities/1/1", json={"owner_id": OTHER_OWNER, "target_qty": 9})
    assert response.status_code == 404
    assert client.get("/target_quantities/1").get_json()["target_qty"] == 3


def test_put_rejects_missing_building_and_item_type(client):
    assert client.put("/target_quantities/999999/1",
                      json={"owner_id": OWNER, "target_qty": 1}).status_code == 404
    assert client.put("/target_quantities/1/999999",
                      json={"owner_id": OWNER, "target_qty": 1}).status_code == 404


@pytest.mark.parametrize("body", [
    {"owner_id": OWNER, "target_qty": -1},
    {"owner_id": OWNER, "target_qty": "5"},
    {"owner_id": OWNER, "target_qty": 2.5},
    {"owner_id": OWNER},
    {"target_qty": 5},
    {},
])
def test_put_rejects_bad_bodies(client, body):
    assert client.put("/target_quantities/1/1", json=body).status_code == 400


def test_delete(client):
    assert client.delete("/target_quantities/1").status_code == 204
    assert client.delete("/target_quantities/1").status_code == 404
