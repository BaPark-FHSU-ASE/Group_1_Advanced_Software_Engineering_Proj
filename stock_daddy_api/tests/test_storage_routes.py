import shutil

import pytest

from app.config import Config
from tests.conftest import _REAL_DB
from tests.route_helpers import *  # noqa: F403  (DALE, JESS, load_app, run_sql, ...)

app = load_app("stock_daddy_api_main_storage_routes")


@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    path = tmp_path / "stockdaddy_storage_routes.db"
    shutil.copyfile(_REAL_DB, path)
    monkeypatch.setattr(Config, "DB_PATH", str(path))
    return path


@pytest.fixture
def client(fresh_db):
    return app.test_client()


def test_owner_retires_an_empty_storage_unit(client, fresh_db):
    storage_id = run_sql(
        fresh_db, "INSERT INTO storage (room_id, storage_type) VALUES (1, 'Empty Shelf')"
    )
    response = retire(client, "storages", storage_id)
    assert response.status_code == 200
    assert response.get_json()["retired"] is not None


def test_storage_with_items_is_blocked_with_a_clear_message(client, fresh_db):
    response = retire(client, "storages", 1)
    assert response.status_code == 409
    assert response.get_json()["error"] == "Can't retire this storage: 9 items still inside"
    assert one_value(fresh_db, "SELECT retired FROM storage WHERE storage_id = 1") is None


def test_employee_cannot_retire_a_storage_unit(client):
    assert_error(retire(client, "storages", 1, user_id=JESS), 403, "owner role is required")


def test_retiring_a_missing_storage_unit_is_404(client):
    assert_error(retire(client, "storages", 999999), 404, "Storage not found")
    
    
def test_lists_hide_retired_storage_units_unless_asked(client, fresh_db):
    storage_id = run_sql(
        fresh_db, "INSERT INTO storage (room_id, storage_type) VALUES (1, 'Empty Shelf')"
    )
    assert storage_id in ids_of(client.get("/storages?user_id=1"), "storage_id")

    retire(client, "storages", storage_id)
    assert storage_id not in ids_of(client.get("/storages?user_id=1"), "storage_id")
    assert storage_id in ids_of(client.get("/storages?user_id=1&include_retired=true"), "storage_id")

def test_cannot_add_a_storage_unit_to_a_retired_room(client, fresh_db):
    room_id = run_sql(
        fresh_db,
        "INSERT INTO room (building_id, location) VALUES (?, 'Empty')",
        (add_empty_building(fresh_db),),
    )
    retire(client, "rooms", room_id)

    response = client.post("/storages", json={"user_id": DALE, "room_id": room_id, "storage_type": "Shelf"})
    assert_error(response, 409, "That room is retired")

# ---- who can see and change storage units -----------------------------------

def _other_business_with_a_room(client, fresh_db):
    """A second business, owned by a new person, with one building and room. -> (person, room_id)"""
    person = add_person(fresh_db)
    business = client.post("/businesses", json={"name": "Other Co", "owner_id": person}).get_json()
    building = client.post(
        "/buildings",
        json={"user_id": person, "business_id": business["business_id"],
              "state": "KS", "city": "Salina", "street_address": "5 Elm St"},
    ).get_json()
    room = client.post(
        "/rooms",
        json={"user_id": person, "building_id": building["building_id"], "location": "Back"},
    ).get_json()
    return person, room["room_id"]


def test_members_see_their_businesses_storage_units(client):
    for user in (DALE, JESS):
        response = client.get(f"/storages?user_id={user}")
        assert response.status_code == 200
        assert len(response.get_json()) == 11


def test_a_stranger_sees_no_storage_units_and_missing_user_id_is_400(client, fresh_db):
    stranger = add_person(fresh_db)
    assert client.get(f"/storages?user_id={stranger}").get_json() == []
    assert_error(client.get("/storages"), 400, "user_id is required")


def test_lists_only_show_storage_units_of_your_own_businesses(client, fresh_db):
    person, room_id = _other_business_with_a_room(client, fresh_db)
    unit = client.post(
        "/storages", json={"user_id": person, "room_id": room_id, "storage_type": "Shelf"}
    ).get_json()
    assert ids_of(client.get(f"/storages?user_id={person}"), "storage_id") == [unit["storage_id"]]
    assert unit["storage_id"] not in ids_of(client.get(f"/storages?user_id={DALE}"), "storage_id")


def test_employee_can_view_a_storage_unit_but_a_stranger_cannot(client, fresh_db):
    assert client.get(f"/storages/1?user_id={JESS}").status_code == 200
    stranger = add_person(fresh_db)
    not_yours = client.get(f"/storages/1?user_id={stranger}")
    missing = client.get(f"/storages/999999?user_id={stranger}")
    assert not_yours.status_code == missing.status_code == 404
    assert not_yours.get_json() == missing.get_json() == {"error": "Storage not found"}
    assert_error(client.get("/storages/1"), 400, "user_id is required")


def test_owner_can_add_a_storage_unit(client):
    response = client.post("/storages", json={"user_id": DALE, "room_id": 1, "storage_type": "Bin"})
    assert response.status_code == 201
    assert response.get_json()["storage_type"] == "Bin"


def test_employee_cannot_add_a_storage_unit(client):
    response = client.post("/storages", json={"user_id": JESS, "room_id": 1, "storage_type": "Bin"})
    assert_error(response, 403, "owner role is required")


def test_stranger_cannot_add_a_storage_unit_to_someone_elses_room(client, fresh_db):
    stranger = add_person(fresh_db)
    response = client.post("/storages", json={"user_id": stranger, "room_id": 1, "storage_type": "Bin"})
    assert_error(response, 404, "Room not found")


def test_owner_can_edit_a_storage_unit(client):
    response = client.put("/storages/1", json={"user_id": DALE, "room_id": 1, "storage_type": "Renamed"})
    assert response.status_code == 200
    assert response.get_json()["storage_type"] == "Renamed"


def test_employee_cannot_edit_a_storage_unit(client):
    response = client.put("/storages/1", json={"user_id": JESS, "room_id": 1, "storage_type": "Renamed"})
    assert_error(response, 403, "owner role is required")


def test_cannot_move_a_storage_unit_into_a_room_you_are_not_in(client, fresh_db):
    _, other_room = _other_business_with_a_room(client, fresh_db)
    before = one_value(fresh_db, "SELECT room_id FROM storage WHERE storage_id = 1")
    response = client.put(
        "/storages/1", json={"user_id": DALE, "room_id": other_room, "storage_type": "Moved"}
    )
    assert_error(response, 404, "Room not found")
    assert one_value(fresh_db, "SELECT room_id FROM storage WHERE storage_id = 1") == before


def test_editing_a_missing_storage_unit_is_404(client):
    response = client.put("/storages/999999", json={"user_id": DALE, "room_id": 1, "storage_type": "X"})
    assert_error(response, 404, "Storage not found")


def test_owner_can_delete_an_unused_storage_unit(client, fresh_db):
    storage_id = run_sql(
        fresh_db, "INSERT INTO storage (room_id, storage_type) VALUES (1, 'Empty Shelf')"
    )
    assert client.delete(f"/storages/{storage_id}?user_id={DALE}").status_code == 204
    assert client.get(f"/storages/{storage_id}?user_id={DALE}").status_code == 404


def test_employee_and_stranger_cannot_delete_a_storage_unit(client, fresh_db):
    storage_id = run_sql(
        fresh_db, "INSERT INTO storage (room_id, storage_type) VALUES (1, 'Empty Shelf')"
    )
    assert_error(client.delete(f"/storages/{storage_id}?user_id={JESS}"), 403, "owner role is required")
    stranger = add_person(fresh_db)
    assert_error(client.delete(f"/storages/{storage_id}?user_id={stranger}"), 404, "Storage not found")
    assert_error(client.delete(f"/storages/{storage_id}"), 400, "user_id is required")
    assert client.get(f"/storages/{storage_id}?user_id={DALE}").status_code == 200