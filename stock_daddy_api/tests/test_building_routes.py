import shutil
 
import pytest
 
from app.config import Config
from tests.conftest import _REAL_DB
from tests.route_helpers import *  # noqa: F403  (DALE, JESS, load_app, run_sql, ...)
 
app = load_app("stock_daddy_api_main_building_routes")
 
 
@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    path = tmp_path / "stockdaddy_building_routes.db"
    shutil.copyfile(_REAL_DB, path)
    monkeypatch.setattr(Config, "DB_PATH", str(path))
    return path
 
 
@pytest.fixture
def client(fresh_db):
    return app.test_client()
 
 
def test_owner_retires_an_empty_building(client, fresh_db):
    building_id = add_empty_building(fresh_db)
    response = retire(client, "buildings", building_id)
    assert response.status_code == 200
    assert response.get_json()["retired"] is not None
    assert client.get(f"/buildings/{building_id}?user_id=1").get_json()["retired"] is not None
 
 
def test_building_with_stuff_inside_is_blocked_with_a_clear_message(client, fresh_db):
    response = retire(client, "buildings", 1)
    assert response.status_code == 409
    body = response.get_json()
    assert body["error"] == (
        "Can't retire this building: 2 rooms, 3 storage units and 40 items still inside"
    )
    assert body["still_inside"] == {"rooms": 2, "storage_units": 3, "items": 40}
    assert one_value(fresh_db, "SELECT retired FROM building WHERE building_id = 1") is None
 
 
def test_employee_cannot_retire_a_building(client, fresh_db):
    building_id = add_empty_building(fresh_db)
    response = retire(client, "buildings", building_id, user_id=JESS)
    assert_error(response, 403, "owner role is required")
 
 
def test_stranger_gets_the_same_404_as_a_missing_building(client, fresh_db):
    stranger = add_person(fresh_db)
    not_yours = retire(client, "buildings", add_empty_building(fresh_db), user_id=stranger)
    missing = retire(client, "buildings", 999999)
    assert not_yours.status_code == missing.status_code == 404
    assert not_yours.get_json() == missing.get_json() == {"error": "Building not found"}
 
 
def test_retiring_a_building_needs_a_user_id(client):
    assert_error(client.post("/buildings/1/retire", json={}), 400, "user_id is required")
 
 
def test_lists_hide_retired_buildings_unless_asked(client, fresh_db):
    building_id = add_empty_building(fresh_db)
    assert building_id in ids_of(client.get("/buildings?user_id=1"), "building_id")
 
    retire(client, "buildings", building_id)
    assert building_id not in ids_of(client.get("/buildings?user_id=1"), "building_id")
    assert building_id in ids_of(client.get("/buildings?user_id=1&include_retired=true"), "building_id")
    assert client.get(f"/buildings/{building_id}?user_id=1").status_code == 200
 
 
def test_include_retired_must_be_true_or_false(client):
    response = client.get("/buildings?user_id=1&include_retired=maybe")
    assert_error(response, 400, "include_retired must be true or false")
 
 
def test_cannot_add_a_building_to_a_retired_business(client):
    business_id = client.post("/businesses", json={"name": "Closed Co", "owner_id": DALE}).get_json()["business_id"]
    retire(client, "businesses", business_id)
 
    body = {"user_id": DALE, "business_id": business_id, "state": "KS", "city": "Hays", "street_address": "9 Closed St"}
    assert_error(client.post("/buildings", json=body), 409, "That business is retired")
 
 
# ---- who can see and change buildings ---------------------------------------
 
NEW_BUILDING = {"state": "KS", "city": "Salina", "street_address": "5 Elm St"}
 
 
def test_members_see_their_businesses_buildings(client):
    for user in (DALE, JESS):
        response = client.get(f"/buildings?user_id={user}")
        assert response.status_code == 200
        assert len(response.get_json()) == 5
 
 
def test_a_stranger_sees_no_buildings_and_missing_user_id_is_400(client, fresh_db):
    stranger = add_person(fresh_db)
    assert client.get(f"/buildings?user_id={stranger}").get_json() == []
    assert_error(client.get("/buildings"), 400, "user_id is required")
 
 
def test_lists_only_show_buildings_of_your_own_businesses(client, fresh_db):
    stranger = add_person(fresh_db)
    other = client.post("/businesses", json={"name": "Other Co", "owner_id": stranger}).get_json()
    created = client.post(
        "/buildings",
        json=dict(NEW_BUILDING, user_id=stranger, business_id=other["business_id"]),
    ).get_json()
    mine = ids_of(client.get(f"/buildings?user_id={stranger}"), "building_id")
    assert mine == [created["building_id"]]
    assert created["building_id"] not in ids_of(client.get("/buildings?user_id=1"), "building_id")
 
 
def test_employee_can_view_a_building_but_a_stranger_cannot(client, fresh_db):
    assert client.get(f"/buildings/1?user_id={JESS}").status_code == 200
    stranger = add_person(fresh_db)
    not_yours = client.get(f"/buildings/1?user_id={stranger}")
    missing = client.get(f"/buildings/999999?user_id={stranger}")
    assert not_yours.status_code == missing.status_code == 404
    assert not_yours.get_json() == missing.get_json() == {"error": "Building not found"}
    assert_error(client.get("/buildings/1"), 400, "user_id is required")
 
 
def test_owner_can_add_a_building(client):
    response = client.post("/buildings", json=dict(NEW_BUILDING, user_id=DALE, business_id=1))
    assert response.status_code == 201
    assert response.get_json()["city"] == "Salina"
 
 
def test_employee_cannot_add_a_building(client):
    response = client.post("/buildings", json=dict(NEW_BUILDING, user_id=JESS, business_id=1))
    assert_error(response, 403, "owner role is required")
 
 
def test_stranger_cannot_add_a_building_to_someone_elses_business(client, fresh_db):
    stranger = add_person(fresh_db)
    response = client.post("/buildings", json=dict(NEW_BUILDING, user_id=stranger, business_id=1))
    assert_error(response, 404, "Business not found")
 
 
def test_owner_can_edit_a_building(client, fresh_db):
    building_id = add_empty_building(fresh_db)
    response = client.put(
        f"/buildings/{building_id}", json=dict(NEW_BUILDING, user_id=DALE, business_id=1)
    )
    assert response.status_code == 200
    assert response.get_json()["street_address"] == "5 Elm St"
 
 
def test_employee_cannot_edit_a_building(client):
    response = client.put("/buildings/1", json=dict(NEW_BUILDING, user_id=JESS, business_id=1))
    assert_error(response, 403, "owner role is required")
 
 
def test_cannot_move_a_building_into_a_business_you_are_not_in(client, fresh_db):
    stranger = add_person(fresh_db)
    other = client.post("/businesses", json={"name": "Other Co", "owner_id": stranger}).get_json()
    # Dale owns building 1 but has no role in Other Co.
    response = client.put(
        "/buildings/1", json=dict(NEW_BUILDING, user_id=DALE, business_id=other["business_id"])
    )
    assert_error(response, 404, "Business not found")
    assert one_value(fresh_db, "SELECT business_id FROM building WHERE building_id = 1") == 1
 
 
def test_editing_a_missing_building_is_404(client):
    response = client.put("/buildings/999999", json=dict(NEW_BUILDING, user_id=DALE, business_id=1))
    assert_error(response, 404, "Building not found")
 
 
def test_owner_can_delete_an_unused_building(client, fresh_db):
    building_id = add_empty_building(fresh_db)
    assert client.delete(f"/buildings/{building_id}?user_id={DALE}").status_code == 204
    assert client.get(f"/buildings/{building_id}?user_id={DALE}").status_code == 404
 
 
def test_employee_and_stranger_cannot_delete_a_building(client, fresh_db):
    building_id = add_empty_building(fresh_db)
    assert_error(client.delete(f"/buildings/{building_id}?user_id={JESS}"), 403, "owner role is required")
    stranger = add_person(fresh_db)
    assert_error(client.delete(f"/buildings/{building_id}?user_id={stranger}"), 404, "Building not found")
    assert_error(client.delete(f"/buildings/{building_id}"), 400, "user_id is required")
    assert client.get(f"/buildings/{building_id}?user_id={DALE}").status_code == 200
 