import shutil

import pytest

from app.config import Config
from tests.conftest import _REAL_DB
from tests.route_helpers import *  
app = load_app("stock_daddy_api_main_room_routes")


@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    path = tmp_path / "stockdaddy_room_routes.db"
    shutil.copyfile(_REAL_DB, path)
    monkeypatch.setattr(Config, "DB_PATH", str(path))
    return path


@pytest.fixture
def client(fresh_db):
    return app.test_client()


def test_owner_retires_an_empty_room(client, fresh_db):
    room_id = run_sql(
        fresh_db,
        "INSERT INTO room (building_id, location) VALUES (?, 'Empty')",
        (add_empty_building(fresh_db),),
    )
    response = retire(client, "rooms", room_id)
    assert response.status_code == 200
    assert response.get_json()["retired"] is not None


def test_room_with_stuff_inside_is_blocked_with_a_clear_message(client, fresh_db):
    response = retire(client, "rooms", 1)
    assert response.status_code == 409
    assert response.get_json()["error"] == (
        "Can't retire this room: 2 storage units and 21 items still inside"
    )
    assert one_value(fresh_db, "SELECT retired FROM room WHERE room_id = 1") is None


def test_retiring_a_whole_room_bottom_up_through_the_api(client, fresh_db):
    assert retire(client, "rooms", 1).status_code == 409

    for storage_id in first_column(fresh_db, "SELECT storage_id FROM storage WHERE room_id = 1"):
        items = first_column(fresh_db, "SELECT item_id FROM item WHERE storage_id = ?", (storage_id,))
        for item_id in items:
            assert retire(client, "items", item_id).status_code == 200
        assert retire(client, "storages", storage_id).status_code == 200

    assert retire(client, "rooms", 1).status_code == 200


def test_employee_cannot_retire_a_room(client):
    assert_error(retire(client, "rooms", 1, user_id=JESS), 403, "owner role is required")


def test_retiring_a_missing_room_is_404(client):
    assert_error(retire(client, "rooms", 999999), 404, "Room not found")
    
def test_lists_hide_retired_rooms_unless_asked(client, fresh_db):
    room_id = run_sql(
        fresh_db,
        "INSERT INTO room (building_id, location) VALUES (?, 'Empty')",
        (add_empty_building(fresh_db),),
    )
    assert room_id in ids_of(client.get("/rooms?user_id=1"), "room_id")

    retire(client, "rooms", room_id)
    assert room_id not in ids_of(client.get("/rooms?user_id=1"), "room_id")
    assert room_id in ids_of(client.get("/rooms?user_id=1&include_retired=true"), "room_id")

def test_cannot_add_a_room_to_a_retired_building(client, fresh_db):
    building_id = add_empty_building(fresh_db)
    retire(client, "buildings", building_id)

    response = client.post("/rooms", json={"user_id": DALE, "building_id": building_id, "location": "Back"})
    assert_error(response, 409, "That building is retired")
    
# ---- who can see and change rooms -------------------------------------------

def _other_business_with_a_building(client, fresh_db):
    """A second business, owned by a new person, with one building. -> (person, building_id)"""
    person = add_person(fresh_db)
    business = client.post("/businesses", json={"name": "Other Co", "owner_id": person}).get_json()
    building = client.post(
        "/buildings",
        json={"user_id": person, "business_id": business["business_id"],
              "state": "KS", "city": "Salina", "street_address": "5 Elm St"},
    ).get_json()
    return person, building["building_id"]


def test_members_see_their_businesses_rooms(client):
    for user in (DALE, JESS):
        response = client.get(f"/rooms?user_id={user}")
        assert response.status_code == 200
        assert len(response.get_json()) == 10


def test_a_stranger_sees_no_rooms_and_missing_user_id_is_400(client, fresh_db):
    stranger = add_person(fresh_db)
    assert client.get(f"/rooms?user_id={stranger}").get_json() == []
    assert_error(client.get("/rooms"), 400, "user_id is required")


def test_lists_only_show_rooms_of_your_own_businesses(client, fresh_db):
    person, building_id = _other_business_with_a_building(client, fresh_db)
    room = client.post(
        "/rooms", json={"user_id": person, "building_id": building_id, "location": "Back"}
    ).get_json()
    assert ids_of(client.get(f"/rooms?user_id={person}"), "room_id") == [room["room_id"]]
    assert room["room_id"] not in ids_of(client.get(f"/rooms?user_id={DALE}"), "room_id")


def test_employee_can_view_a_room_but_a_stranger_cannot(client, fresh_db):
    assert client.get(f"/rooms/1?user_id={JESS}").status_code == 200
    stranger = add_person(fresh_db)
    not_yours = client.get(f"/rooms/1?user_id={stranger}")
    missing = client.get(f"/rooms/999999?user_id={stranger}")
    assert not_yours.status_code == missing.status_code == 404
    assert not_yours.get_json() == missing.get_json() == {"error": "Room not found"}
    assert_error(client.get("/rooms/1"), 400, "user_id is required")


def test_owner_can_add_a_room(client):
    response = client.post("/rooms", json={"user_id": DALE, "building_id": 1, "location": "Annex"})
    assert response.status_code == 201
    assert response.get_json()["location"] == "Annex"


def test_employee_cannot_add_a_room(client):
    response = client.post("/rooms", json={"user_id": JESS, "building_id": 1, "location": "Annex"})
    assert_error(response, 403, "owner role is required")


def test_stranger_cannot_add_a_room_to_someone_elses_building(client, fresh_db):
    stranger = add_person(fresh_db)
    response = client.post("/rooms", json={"user_id": stranger, "building_id": 1, "location": "Annex"})
    assert_error(response, 404, "Building not found")


def test_owner_can_edit_a_room(client):
    response = client.put("/rooms/1", json={"user_id": DALE, "building_id": 1, "location": "Renamed"})
    assert response.status_code == 200
    assert response.get_json()["location"] == "Renamed"


def test_employee_cannot_edit_a_room(client):
    response = client.put("/rooms/1", json={"user_id": JESS, "building_id": 1, "location": "Renamed"})
    assert_error(response, 403, "owner role is required")


def test_cannot_move_a_room_into_a_building_you_are_not_in(client, fresh_db):
    _, other_building = _other_business_with_a_building(client, fresh_db)
    before = one_value(fresh_db, "SELECT building_id FROM room WHERE room_id = 1")
    response = client.put(
        "/rooms/1", json={"user_id": DALE, "building_id": other_building, "location": "Moved"}
    )
    assert_error(response, 404, "Building not found")
    assert one_value(fresh_db, "SELECT building_id FROM room WHERE room_id = 1") == before


def test_editing_a_missing_room_is_404(client):
    response = client.put("/rooms/999999", json={"user_id": DALE, "building_id": 1, "location": "X"})
    assert_error(response, 404, "Room not found")


def test_owner_can_delete_an_unused_room(client, fresh_db):
    room_id = run_sql(
        fresh_db,
        "INSERT INTO room (building_id, location) VALUES (?, 'Empty')",
        (add_empty_building(fresh_db),),
    )
    assert client.delete(f"/rooms/{room_id}?user_id={DALE}").status_code == 204
    assert client.get(f"/rooms/{room_id}?user_id={DALE}").status_code == 404


def test_employee_and_stranger_cannot_delete_a_room(client, fresh_db):
    room_id = run_sql(
        fresh_db,
        "INSERT INTO room (building_id, location) VALUES (?, 'Empty')",
        (add_empty_building(fresh_db),),
    )
    assert_error(client.delete(f"/rooms/{room_id}?user_id={JESS}"), 403, "owner role is required")
    stranger = add_person(fresh_db)
    assert_error(client.delete(f"/rooms/{room_id}?user_id={stranger}"), 404, "Room not found")
    assert_error(client.delete(f"/rooms/{room_id}"), 400, "user_id is required")
    assert client.get(f"/rooms/{room_id}?user_id={DALE}").status_code == 200    
