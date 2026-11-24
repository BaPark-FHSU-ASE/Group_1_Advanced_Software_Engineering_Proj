import shutil

import pytest
from werkzeug.security import check_password_hash
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

NEW_PERSON = {"first_name": "New", "last_name": "Person", "email": "new@example.com", "password": "longenough"}


def test_register_makes_an_account_and_no_secret_comes_back(client, fresh_db):
    response = client.post("/auth/register", json=NEW_PERSON)
    assert response.status_code == 201
    body = response.get_json()
    assert set(body) == {"owner_id", "first_name", "last_name", "email", "memberships"}
    assert body["email"] == "new@example.com"
    assert body["memberships"] == []

    stored = one_value(fresh_db, "SELECT password_hash FROM owners WHERE owner_id = ?", (body["owner_id"],))
    assert stored != "longenough"
    assert check_password_hash(stored, "longenough")


def test_register_trims_names_and_email_but_not_the_password(client, fresh_db):
    person = {"first_name": "  Ada ", "last_name": " Lovelace  ", "email": "  ada@example.com ", "password": "  spaced out  "}
    body = client.post("/auth/register", json=person).get_json()
    assert (body["first_name"], body["last_name"], body["email"]) == ("Ada", "Lovelace", "ada@example.com")

    stored = one_value(fresh_db, "SELECT password_hash FROM owners WHERE owner_id = ?", (body["owner_id"],))
    assert check_password_hash(stored, "  spaced out  ")
    assert not check_password_hash(stored, "spaced out")


def test_register_refuses_a_taken_email_whatever_the_capitals(client):
    taken = "An account with that email already exists."
    assert client.post("/auth/register", json=NEW_PERSON).status_code == 201
    for email in ("new@example.com", "NEW@Example.com", "DALE@prairieroofing.example"):
        response = client.post("/auth/register", json=dict(NEW_PERSON, email=email))
        assert response.status_code == 409
        assert response.get_json() == {"error": taken}


def test_register_says_what_is_missing_in_plain_sentences(client):
    assert_error(
        client.post("/auth/register", json={}), 400,
        "First name is required. Last name is required. Email is required. Password is required.",
    )
    assert_error(client.post("/auth/register", json=dict(NEW_PERSON, first_name="   ")), 400, "First name is required.")
    assert_error(client.post("/auth/register", json=dict(NEW_PERSON, email=None)), 400, "Email is required.")
    assert_error(client.post("/auth/register", json=dict(NEW_PERSON, last_name=12)), 400, "Last name must be text.")
    assert_error(client.post("/auth/register", json=dict(NEW_PERSON, first_name="x" * 101)), 400, "First name must be 100 characters or fewer.")


def test_register_checks_the_password_and_the_email(client):
    too_short = "Password must be at least 8 characters."
    assert_error(client.post("/auth/register", json=dict(NEW_PERSON, password="1234567")), 400, too_short)
    assert client.post("/auth/register", json=dict(NEW_PERSON, password="12345678")).status_code == 201
    for bad in ("not-an-email", "two@@example.com", "no dots@example", "a b@example.com"):
        assert_error(client.post("/auth/register", json=dict(NEW_PERSON, email=bad)), 400, "Enter a valid email address.")


def test_register_needs_a_json_object(client):
    assert_error(client.post("/auth/register", data="hello"), 400, "Request body must be a JSON object")
    assert_error(client.post("/auth/register", json=["a"]), 400, "Request body must be a JSON object")


def test_the_old_create_account_route_is_gone(client):
    assert client.post("/owners", json=NEW_PERSON).status_code == 405



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