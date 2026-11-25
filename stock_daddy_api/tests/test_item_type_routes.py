import shutil

import pytest

from app.config import Config
from tests.conftest import _REAL_DB
from tests.route_helpers import *  # noqa: F403  (DALE, JESS, load_app, run_sql, ...)

app = load_app("stock_daddy_api_main_item_type_routes")


@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    path = tmp_path / "stockdaddy_item_type_routes.db"
    shutil.copyfile(_REAL_DB, path)
    monkeypatch.setattr(Config, "DB_PATH", str(path))
    return path


@pytest.fixture
def client(fresh_db):
    return app.test_client()


def _other_business_owner(fresh_db, item_type_id=None):
    person = add_person(fresh_db, "boss@other.example")
    business = run_sql(fresh_db, "INSERT INTO business (name, owner_id) VALUES ('Other Co', ?)", (person,))
    run_sql(
        fresh_db,
        "INSERT INTO business_member (business_id, owner_id, role) VALUES (?, ?, 'owner')",
        (business, person),
    )
    if item_type_id is not None:
        building = run_sql(
            fresh_db,
            "INSERT INTO building (business_id, state, city, street_address) "
            "VALUES (?, 'KS', 'Salina', '5 Elm St')",
            (business,),
        )
        room = run_sql(fresh_db, "INSERT INTO room (building_id, location) VALUES (?, 'Back')", (building,))
        storage = run_sql(fresh_db, "INSERT INTO storage (room_id, storage_type) VALUES (?, 'Shelf')", (room,))
        run_sql(
            fresh_db,
            "INSERT INTO item (item_type_id, storage_id, item_name) VALUES (?, ?, 'Other Item')",
            (item_type_id, storage),
        )
    return person


def test_members_see_item_types_and_strangers_see_none(client, fresh_db):
    for user in (DALE, JESS):
        response = client.get(f"/item_types?user_id={user}")
        assert response.status_code == 200
        assert len(response.get_json()) == 6
    stranger = add_person(fresh_db)
    assert client.get(f"/item_types?user_id={stranger}").get_json() == []
    assert_error(client.get("/item_types"), 400, "user_id is required")


def test_employee_can_view_an_item_type_but_a_stranger_cannot(client, fresh_db):
    assert client.get(f"/item_types/1?user_id={JESS}").status_code == 200
    stranger = add_person(fresh_db)
    assert_error(client.get(f"/item_types/1?user_id={stranger}"), 404, "Item type not found")
    assert_error(client.get(f"/item_types/999999?user_id={JESS}"), 404, "Item type not found")
    assert_error(client.get("/item_types/1"), 400, "user_id is required")


def test_owner_can_add_an_item_type(client):
    body = {"user_id": DALE, "name": "Ladder Strap", "description": "Heavy duty", "replacement_cost": 12.5}
    response = client.post("/item_types", json=body)
    assert response.status_code == 201
    assert response.get_json()["name"] == "Ladder Strap"


def test_any_business_owner_can_add_an_item_type(client, fresh_db):
    boss = _other_business_owner(fresh_db)
    response = client.post("/item_types", json={"user_id": boss, "name": "Safety Cone"})
    assert response.status_code == 201


def test_employee_and_stranger_cannot_add_an_item_type(client, fresh_db):
    assert_error(
        client.post("/item_types", json={"user_id": JESS, "name": "Cone"}), 403, "owner role is required"
    )
    stranger = add_person(fresh_db)
    assert_error(
        client.post("/item_types", json={"user_id": stranger, "name": "Cone"}), 403, "owner role is required"
    )
    assert_error(client.post("/item_types", json={"name": "Cone"}), 400, "user_id is required")


def test_owner_can_edit_a_type_only_their_own_business_uses(client):
    response = client.put(
        "/item_types/1", json={"user_id": DALE, "name": "Renamed Type", "description": "New text"}
    )
    assert response.status_code == 200
    assert response.get_json()["name"] == "Renamed Type"


def test_employee_cannot_edit_or_delete_an_item_type(client):
    assert_error(
        client.put("/item_types/1", json={"user_id": JESS, "name": "X"}), 403, "owner role is required"
    )
    assert_error(client.delete(f"/item_types/1?user_id={JESS}"), 403, "owner role is required")


def test_cannot_change_a_type_that_another_business_uses(client, fresh_db):
    boss = _other_business_owner(fresh_db, item_type_id=1)
    # Business 1 and the other business both have type 1 items, so neither
    # owner can change it on their own.
    for user in (DALE, boss):
        edited = client.put("/item_types/1", json={"user_id": user, "name": "Hijacked"})
        assert_error(edited, 403, "Another business uses this item type")
        deleted = client.delete(f"/item_types/1?user_id={user}")
        assert_error(deleted, 403, "Another business uses this item type")
    assert client.get(f"/item_types/1?user_id={DALE}").get_json()["name"] != "Hijacked"


def test_a_type_nobody_uses_can_be_edited_and_deleted(client):
    created = client.post("/item_types", json={"user_id": DALE, "name": "Spare Part"}).get_json()
    type_id = created["item_type_id"]
    edited = client.put(f"/item_types/{type_id}", json={"user_id": DALE, "name": "Spare Part 2"})
    assert edited.status_code == 200
    assert client.delete(f"/item_types/{type_id}?user_id={DALE}").status_code == 204
    assert_error(client.get(f"/item_types/{type_id}?user_id={DALE}"), 404, "Item type not found")


def test_editing_or_deleting_a_missing_type_is_404(client):
    assert_error(
        client.put("/item_types/999999", json={"user_id": DALE, "name": "X"}), 404, "Item type not found"
    )
    assert_error(client.delete(f"/item_types/999999?user_id={DALE}"), 404, "Item type not found")


def test_deleting_a_type_your_own_items_use_is_refused_by_the_database(client):
    assert_error(client.delete(f"/item_types/1?user_id={DALE}"), 409, "still depend")
    assert client.get(f"/item_types/1?user_id={DALE}").status_code == 200



# Seed: Nail Gun (type 1) lasts 730 days, Hard Hat (type 4) 1825, the rest have no limit.

def test_item_types_show_their_service_life(client):
    listed = {t["item_type_id"]: t["service_life_days"] for t in client.get(f"/item_types?user_id={DALE}").get_json()}
    assert listed == {1: 730, 2: None, 3: None, 4: 1825, 5: None, 6: None}
    assert client.get(f"/item_types/1?user_id={JESS}").get_json()["service_life_days"] == 730


def test_an_item_type_can_be_added_with_or_without_a_service_life(client):
    with_life = client.post("/item_types", json={"user_id": DALE, "name": "Short Lived", "service_life_days": 30})
    assert with_life.status_code == 201
    assert with_life.get_json()["service_life_days"] == 30

    without = client.post("/item_types", json={"user_id": DALE, "name": "Forever"}).get_json()
    assert without["service_life_days"] is None
    nulled = client.post("/item_types", json={"user_id": DALE, "name": "Also Forever", "service_life_days": None}).get_json()
    assert nulled["service_life_days"] is None


def test_service_life_must_be_a_whole_number_of_days_of_at_least_one(client):
    for days in (0, -5):
        response = client.post("/item_types", json={"user_id": DALE, "name": "Bad Life", "service_life_days": days})
        assert_error(response, 400, "Service life must be at least 1 day.")
    for days in (2.5, "abc", True):
        response = client.post("/item_types", json={"user_id": DALE, "name": "Bad Life", "service_life_days": days})
        assert_error(response, 400, "service_life_days must be a whole number")
    names = [t["name"] for t in client.get(f"/item_types?user_id={DALE}").get_json()]
    assert "Bad Life" not in names


def test_editing_an_item_type_sets_or_clears_its_service_life(client):
    body = {"user_id": DALE, "name": "Nail Gun", "service_life_days": 900}
    assert client.put("/item_types/1", json=body).get_json()["service_life_days"] == 900

    # An edit is a full replacement, so leaving the field out clears it.
    cleared = client.put("/item_types/1", json={"user_id": DALE, "name": "Nail Gun"})
    assert cleared.get_json()["service_life_days"] is None


def test_a_bad_service_life_on_an_edit_changes_nothing(client):
    response = client.put("/item_types/1", json={"user_id": DALE, "name": "Renamed", "service_life_days": 0})
    assert_error(response, 400, "Service life must be at least 1 day.")
    kept = client.get(f"/item_types/1?user_id={DALE}").get_json()
    assert (kept["name"], kept["service_life_days"]) == ("Nail Gun", 730)