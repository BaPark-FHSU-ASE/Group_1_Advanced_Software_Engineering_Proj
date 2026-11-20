import shutil

import pytest

from app.config import Config
from tests.conftest import _REAL_DB
from tests.route_helpers import *  # noqa: F403  (DALE, JESS, load_app, run_sql, ...)

app = load_app("stock_daddy_api_main_business_routes")


@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    path = tmp_path / "stockdaddy_business_routes.db"
    shutil.copyfile(_REAL_DB, path)
    monkeypatch.setattr(Config, "DB_PATH", str(path))
    return path


@pytest.fixture
def client(fresh_db):
    return app.test_client()


def test_owner_retires_an_empty_business(client):
    created = client.post("/businesses", json={"name": "Brand New Co", "owner_id": DALE}).get_json()
    response = retire(client, "businesses", created["business_id"])
    assert response.status_code == 200
    assert response.get_json()["retired"] is not None


def test_business_with_buildings_is_blocked_with_a_clear_message(client, fresh_db):
    response = retire(client, "businesses", 1)
    assert response.status_code == 409
    assert response.get_json()["error"] == (
        "Can't retire this business: 5 buildings, 10 rooms, 11 storage units "
        "and 91 items still inside"
    )
    assert one_value(fresh_db, "SELECT retired FROM business WHERE business_id = 1") is None


def test_employee_cannot_retire_a_business(client):
    assert_error(retire(client, "businesses", 1, user_id=JESS), 403, "owner role is required")


def test_retiring_a_missing_business_is_404(client):
    assert_error(retire(client, "businesses", 999999), 404, "Business not found")
    
def test_lists_hide_retired_businesses_unless_asked(client):
    created = client.post("/businesses", json={"name": "Short Lived Co", "owner_id": DALE}).get_json()
    business_id = created["business_id"]
    assert business_id in ids_of(client.get("/businesses?user_id=1"), "business_id")

    retire(client, "businesses", business_id)
    assert business_id not in ids_of(client.get("/businesses?user_id=1"), "business_id")
    assert business_id in ids_of(client.get("/businesses?user_id=1&include_retired=true"), "business_id")
    
# ---- who can see and change businesses --------------------------------------

def test_members_see_their_business(client):
    for user in (DALE, JESS):
        response = client.get(f"/businesses?user_id={user}")
        assert response.status_code == 200
        assert ids_of(response, "business_id") == [1]


def test_a_stranger_sees_no_businesses_and_missing_user_id_is_400(client, fresh_db):
    stranger = add_person(fresh_db)
    assert client.get(f"/businesses?user_id={stranger}").get_json() == []
    assert_error(client.get("/businesses"), 400, "user_id is required")


def test_lists_only_show_your_own_businesses(client, fresh_db):
    person = add_person(fresh_db)
    other = client.post("/businesses", json={"name": "Other Co", "owner_id": person}).get_json()
    assert ids_of(client.get(f"/businesses?user_id={person}"), "business_id") == [other["business_id"]]
    assert other["business_id"] not in ids_of(client.get(f"/businesses?user_id={DALE}"), "business_id")


def test_employee_can_view_a_business_but_a_stranger_cannot(client, fresh_db):
    assert client.get(f"/businesses/1?user_id={JESS}").status_code == 200
    stranger = add_person(fresh_db)
    not_yours = client.get(f"/businesses/1?user_id={stranger}")
    missing = client.get(f"/businesses/999999?user_id={stranger}")
    assert not_yours.status_code == missing.status_code == 404
    assert not_yours.get_json() == missing.get_json() == {"error": "Business not found"}
    assert_error(client.get("/businesses/1"), 400, "user_id is required")


def test_owner_can_rename_a_business_and_the_founder_stays_the_same(client):
    before = client.get(f"/businesses/1?user_id={DALE}").get_json()
    response = client.put("/businesses/1", json={"user_id": DALE, "name": "Renamed Co"})
    assert response.status_code == 200
    assert response.get_json()["name"] == "Renamed Co"
    assert response.get_json()["owner_id"] == before["owner_id"]


def test_employee_stranger_and_missing_business_cannot_be_renamed(client, fresh_db):
    assert_error(
        client.put("/businesses/1", json={"user_id": JESS, "name": "X"}), 403, "owner role is required"
    )
    stranger = add_person(fresh_db)
    assert_error(
        client.put("/businesses/1", json={"user_id": stranger, "name": "X"}), 404, "Business not found"
    )
    assert_error(
        client.put("/businesses/999999", json={"user_id": DALE, "name": "X"}), 404, "Business not found"
    )
    assert_error(client.put("/businesses/1", json={"user_id": DALE}), 400, "name is required")


def test_owner_can_delete_an_unused_business_and_its_team_goes_with_it(client, fresh_db):
    created = client.post("/businesses", json={"name": "Oops Co", "owner_id": DALE}).get_json()
    business_id = created["business_id"]
    assert client.delete(f"/businesses/{business_id}?user_id={DALE}").status_code == 204
    assert client.get(f"/businesses/{business_id}?user_id={DALE}").status_code == 404
    assert one_value(
        fresh_db, "SELECT COUNT(*) FROM business_member WHERE business_id = ?", (business_id,)
    ) == 0


def test_a_business_with_buildings_cannot_be_deleted_and_keeps_its_team(client, fresh_db):
    assert_error(client.delete(f"/businesses/1?user_id={DALE}"), 409, "still depend")
    assert one_value(fresh_db, "SELECT COUNT(*) FROM business_member WHERE business_id = 1") == 2
    assert client.get(f"/businesses/1?user_id={DALE}").status_code == 200


def test_employee_and_stranger_cannot_delete_a_business(client, fresh_db):
    created = client.post("/businesses", json={"name": "Keep Co", "owner_id": DALE}).get_json()
    business_id = created["business_id"]
    client.post(
        f"/businesses/{business_id}/members",
        json={"user_id": DALE, "owner_id": JESS, "role": "employee"},
    )
    assert_error(client.delete(f"/businesses/{business_id}?user_id={JESS}"), 403, "owner role is required")
    stranger = add_person(fresh_db)
    assert_error(client.delete(f"/businesses/{business_id}?user_id={stranger}"), 404, "Business not found")
    assert_error(client.delete(f"/businesses/{business_id}"), 400, "user_id is required")
    assert client.get(f"/businesses/{business_id}?user_id={DALE}").status_code == 200    