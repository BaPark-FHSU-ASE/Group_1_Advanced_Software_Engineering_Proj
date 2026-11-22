import shutil

import pytest

from app.config import Config
from tests.conftest import _REAL_DB
from tests.route_helpers import *  

app = load_app("stock_daddy_api_main_owner_routes")


@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    path = tmp_path / "stockdaddy_owner_routes.db"
    shutil.copyfile(_REAL_DB, path)
    monkeypatch.setattr(Config, "DB_PATH", str(path))
    return path


@pytest.fixture
def client(fresh_db):
    return app.test_client()


NEW_PERSON = {"first_name": "New", "last_name": "Person", "email": "new@example.com", "password_hash": "h"}


def test_anyone_can_register_and_the_hash_never_comes_back(client):
    response = client.post("/owners", json=NEW_PERSON)
    assert response.status_code == 201
    assert "password_hash" not in response.get_json()
    assert response.get_json()["email"] == "new@example.com"


def test_lists_show_you_and_the_people_you_share_a_business_with(client, fresh_db):
    for user in (DALE, JESS):
        response = client.get(f"/owners?user_id={user}")
        assert response.status_code == 200
        assert sorted(ids_of(response, "owner_id")) == [DALE, JESS]
        assert all("password_hash" not in row for row in response.get_json())

    stranger = add_person(fresh_db)
    assert ids_of(client.get(f"/owners?user_id={stranger}"), "owner_id") == [stranger]
    assert_error(client.get("/owners"), 400, "user_id is required")


def test_other_businesses_people_are_not_listed(client, fresh_db):
    boss = add_person(fresh_db, "boss@other.example")
    client.post("/businesses", json={"name": "Other Co", "owner_id": boss})
    assert ids_of(client.get(f"/owners?user_id={boss}"), "owner_id") == [boss]
    assert boss not in ids_of(client.get(f"/owners?user_id={DALE}"), "owner_id")


def test_you_can_view_yourself_and_a_teammate_but_not_a_stranger(client, fresh_db):
    assert client.get(f"/owners/{DALE}?user_id={DALE}").status_code == 200
    assert client.get(f"/owners/{JESS}?user_id={DALE}").status_code == 200

    stranger = add_person(fresh_db)
    not_visible = client.get(f"/owners/{DALE}?user_id={stranger}")
    missing = client.get(f"/owners/999999?user_id={stranger}")
    assert not_visible.status_code == missing.status_code == 404
    assert not_visible.get_json() == missing.get_json() == {"error": "Owner not found"}
    assert_error(client.get(f"/owners/{DALE}"), 400, "user_id is required")


def test_you_can_edit_yourself(client):
    body = {"user_id": JESS, "first_name": "Jessica", "last_name": "Lee", "email": "jess.new@example.com"}
    response = client.put(f"/owners/{JESS}", json=body)
    assert response.status_code == 200
    assert response.get_json()["first_name"] == "Jessica"


def test_you_cannot_edit_a_teammate_or_a_stranger(client, fresh_db):
    body = {"user_id": DALE, "first_name": "X", "last_name": "Y", "email": "x@example.com"}
    assert_error(client.put(f"/owners/{JESS}", json=body), 403, "only change your own account")

    stranger = add_person(fresh_db)
    assert_error(client.put(f"/owners/{DALE}", json=dict(body, user_id=stranger)), 404, "Owner not found")
    assert_error(client.put(f"/owners/{DALE}", json={"first_name": "X"}), 400, "user_id is required")


def test_you_can_delete_your_own_account_if_nothing_depends_on_it(client, fresh_db):
    loner = add_person(fresh_db, "loner@example.com")
    assert client.delete(f"/owners/{loner}?user_id={loner}").status_code == 204
    assert_error(client.get(f"/owners/{loner}?user_id={loner}"), 404, "Owner not found")


def test_you_cannot_delete_your_account_while_you_belong_to_a_business(client):
    assert_error(client.delete(f"/owners/{JESS}?user_id={JESS}"), 409, "still depend")


def test_you_cannot_delete_a_teammate_or_a_stranger(client, fresh_db):
    assert_error(client.delete(f"/owners/{JESS}?user_id={DALE}"), 403, "only change your own account")
    stranger = add_person(fresh_db)
    assert_error(client.delete(f"/owners/{DALE}?user_id={stranger}"), 404, "Owner not found")
    assert_error(client.delete(f"/owners/{DALE}"), 400, "user_id is required")