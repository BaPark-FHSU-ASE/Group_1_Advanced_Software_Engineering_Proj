import shutil

import pytest

from app.config import Config
from tests.conftest import _REAL_DB
from tests.route_helpers import *  

app = load_app("stock_daddy_api_main_item_routes")


@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    path = tmp_path / "stockdaddy_item_routes.db"
    shutil.copyfile(_REAL_DB, path)
    monkeypatch.setattr(Config, "DB_PATH", str(path))
    return path


@pytest.fixture
def client(fresh_db):
    return app.test_client()


def test_retiring_an_item_keeps_its_history(client, fresh_db):
    movements_before = one_value(fresh_db, "SELECT COUNT(*) FROM item_movement")
    response = retire(client, "items", 1)
    assert response.status_code == 200
    assert response.get_json()["retired"] is not None
    assert one_value(fresh_db, "SELECT COUNT(*) FROM item_movement") == movements_before
    assert one_value(fresh_db, "SELECT COUNT(*) FROM item WHERE item_id = 1") == 1


def test_retiring_twice_just_returns_the_record(client):
    first = retire(client, "items", 1).get_json()
    second = retire(client, "items", 1)
    assert second.status_code == 200
    assert second.get_json()["retired"] == first["retired"]


def test_in_transit_item_can_still_be_retired_by_its_owner(client, fresh_db):
    storage = one_value(fresh_db, "SELECT storage_id FROM item WHERE item_id = 1")
    run_sql(fresh_db, "UPDATE item SET storage_id = NULL, item_status = 'In Transit' WHERE item_id = 1")
    run_sql(fresh_db, "INSERT INTO item_movement (item_id, from_storage_id) VALUES (1, ?)", (storage,))
    assert retire(client, "items", 1).status_code == 200


def test_employee_cannot_retire_an_item(client):
    assert_error(retire(client, "items", 1, user_id=JESS), 403, "owner role is required")


def test_owner_of_another_business_cannot_retire_this_item(client, fresh_db):
    boss = add_person(fresh_db, "boss@other.example")
    client.post("/businesses", json={"name": "Other Co", "owner_id": boss})
    assert_error(retire(client, "items", 1, user_id=boss), 404, "Item not found")
    assert one_value(fresh_db, "SELECT retired FROM item WHERE item_id = 1") is None


def test_retiring_a_missing_item_is_404(client):
    assert_error(retire(client, "items", 999999), 404, "Item not found")
    
    
def test_lists_hide_retired_items_unless_asked(client):
    everything = ids_of(client.get("/items?user_id=1"), "item_id")
    assert 1 in everything

    retire(client, "items", 1)
    after = ids_of(client.get("/items?user_id=1"), "item_id")
    assert 1 not in after
    assert len(after) == len(everything) - 1
    assert sorted(ids_of(client.get("/items?user_id=1&include_retired=true"), "item_id")) == sorted(everything)

def test_cannot_add_or_move_an_item_into_a_retired_storage_unit(client, fresh_db):
    storage_id = run_sql(
        fresh_db, "INSERT INTO storage (room_id, storage_type) VALUES (1, 'Closing Shelf')"
    )
    retire(client, "storages", storage_id)

    added = client.post(
        "/items", json={"user_id": DALE, "item_type_id": 1, "storage_id": storage_id}
    )
    assert_error(added, 409, "That storage unit is retired")

    moved = client.put(
        "/items/1",
        json={"user_id": DALE, "item_type_id": 1, "storage_id": storage_id, "item_status": "In Storage"},
    )
    assert_error(moved, 409, "That storage unit is retired")

def test_a_new_item_needs_a_storage_unit(client):
    response = client.post("/items", json={"user_id": DALE, "item_type_id": 1})
    assert_error(response, 400, "storage_id is required")

# ---- who can see and change items -------------------------------------------

def _other_business_with_a_storage_unit(client, fresh_db):
    """A second business, owned by a new person, with one storage unit. -> (person, storage_id)"""
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
    unit = client.post(
        "/storages", json={"user_id": person, "room_id": room["room_id"], "storage_type": "Shelf"}
    ).get_json()
    return person, unit["storage_id"]


def _body_for(client, item_id, user_id, **changes):
    """A full PUT body that repeats the item as it is now, with `changes` applied."""
    item = client.get(f"/items/{item_id}?user_id={DALE}").get_json()
    body = {
        "user_id": user_id,
        "item_type_id": item["item_type_id"],
        "storage_id": item["storage_id"],
        "item_name": item["item_name"],
        "item_status": item["item_status"],
    }
    body.update(changes)
    return body


def test_members_see_their_businesses_items_including_ones_in_transit(client):
    for user in (DALE, JESS):
        response = client.get(f"/items?user_id={user}")
        assert response.status_code == 200
        assert len(response.get_json()) == 92
        assert 92 in ids_of(response, "item_id")  # item 92 is in transit, no storage unit


def test_a_stranger_sees_no_items_and_missing_user_id_is_400(client, fresh_db):
    stranger = add_person(fresh_db)
    assert client.get(f"/items?user_id={stranger}").get_json() == []
    assert_error(client.get("/items"), 400, "user_id is required")


def test_lists_only_show_items_of_your_own_businesses(client, fresh_db):
    person, storage_id = _other_business_with_a_storage_unit(client, fresh_db)
    item = client.post(
        "/items", json={"user_id": person, "item_type_id": 1, "storage_id": storage_id}
    ).get_json()
    assert ids_of(client.get(f"/items?user_id={person}"), "item_id") == [item["item_id"]]
    assert item["item_id"] not in ids_of(client.get(f"/items?user_id={DALE}"), "item_id")


def test_employee_can_view_an_item_but_a_stranger_cannot(client, fresh_db):
    assert client.get(f"/items/1?user_id={JESS}").status_code == 200
    stranger = add_person(fresh_db)
    not_yours = client.get(f"/items/1?user_id={stranger}")
    missing = client.get(f"/items/999999?user_id={stranger}")
    assert not_yours.status_code == missing.status_code == 404
    assert not_yours.get_json() == missing.get_json() == {"error": "Item not found"}
    assert_error(client.get("/items/1"), 400, "user_id is required")


def test_owner_and_employee_can_both_add_an_item(client):
    for user in (DALE, JESS):
        response = client.post(
            "/items",
            json={"user_id": user, "item_type_id": 1, "storage_id": 1, "item_name": "New Drill"},
        )
        assert response.status_code == 201
        assert response.get_json()["item_status"] == "In Storage"


def test_stranger_cannot_add_an_item_to_someone_elses_storage_unit(client, fresh_db):
    stranger = add_person(fresh_db)
    response = client.post(
        "/items", json={"user_id": stranger, "item_type_id": 1, "storage_id": 1}
    )
    assert_error(response, 404, "Storage not found")


def test_employee_can_change_an_items_status(client):
    new_status = "In Use" if client.get(f"/items/1?user_id={JESS}").get_json()["item_status"] != "In Use" else "In Storage"
    response = client.put("/items/1", json=_body_for(client, 1, JESS, item_status=new_status))
    assert response.status_code == 200
    assert response.get_json()["item_status"] == new_status

    in_transit = client.put("/items/1", json=_body_for(client, 1, JESS, item_status="In Transit"))
    assert in_transit.status_code == 200
    assert in_transit.get_json()["storage_id"] is not None


def test_employee_can_move_an_item_to_another_storage_unit(client):
    response = client.put("/items/1", json=_body_for(client, 1, JESS, storage_id=2))
    assert response.status_code == 200
    assert response.get_json()["storage_id"] == 2


def test_employee_cannot_rename_or_retype_an_item(client):
    renamed = client.put("/items/1", json=_body_for(client, 1, JESS, item_name="Renamed"))
    assert_error(renamed, 403, "owner role is required")

    retyped = client.put("/items/1", json=_body_for(client, 1, JESS, item_type_id=2))
    assert_error(retyped, 403, "owner role is required")

def test_owner_can_rename_and_move_an_item(client):
    response = client.put(
        "/items/1", json=_body_for(client, 1, DALE, item_name="Renamed", storage_id=2)
    )
    assert response.status_code == 200
    assert response.get_json()["item_name"] == "Renamed"
    assert response.get_json()["storage_id"] == 2


def test_cannot_move_an_item_into_a_storage_unit_you_are_not_in(client, fresh_db):
    _, other_storage = _other_business_with_a_storage_unit(client, fresh_db)
    before = one_value(fresh_db, "SELECT storage_id FROM item WHERE item_id = 1")
    response = client.put("/items/1", json=_body_for(client, 1, DALE, storage_id=other_storage))
    assert_error(response, 404, "Storage not found")
    assert one_value(fresh_db, "SELECT storage_id FROM item WHERE item_id = 1") == before


def test_editing_a_missing_item_or_someone_elses_item_is_404(client, fresh_db):
    stranger = add_person(fresh_db)
    body = {"user_id": stranger, "item_type_id": 1, "storage_id": 1, "item_status": "In Use"}
    assert_error(client.put("/items/1", json=body), 404, "Item not found")
    assert_error(client.put("/items/999999", json=dict(body, user_id=DALE)), 404, "Item not found")


def test_owner_can_delete_an_item_with_no_history(client):
    item = client.post(
        "/items", json={"user_id": DALE, "item_type_id": 1, "storage_id": 1}
    ).get_json()
    assert client.delete(f"/items/{item['item_id']}?user_id={DALE}").status_code == 204
    assert client.get(f"/items/{item['item_id']}?user_id={DALE}").status_code == 404


def test_employee_and_stranger_cannot_delete_an_item(client, fresh_db):
    item = client.post(
        "/items", json={"user_id": DALE, "item_type_id": 1, "storage_id": 1}
    ).get_json()
    item_id = item["item_id"]
    assert_error(client.delete(f"/items/{item_id}?user_id={JESS}"), 403, "owner role is required")
    stranger = add_person(fresh_db)
    assert_error(client.delete(f"/items/{item_id}?user_id={stranger}"), 404, "Item not found")
    assert_error(client.delete(f"/items/{item_id}"), 400, "user_id is required")
    assert client.get(f"/items/{item_id}?user_id={DALE}").status_code == 200