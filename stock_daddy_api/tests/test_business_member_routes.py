"""Route tests for /businesses/<id>/members (team members + roles).

Seed data: business 1 has Dale (owner_id 1, owner) and Jess (owner_id 2,
employee). member ids: Dale = 1, Jess = 2.
"""

import importlib.util
import shutil
import sqlite3
from pathlib import Path

import pytest

from app.config import Config
from tests.conftest import _REAL_DB

_spec = importlib.util.spec_from_file_location(
    "stock_daddy_api_main_members", Path(__file__).resolve().parent.parent / "app.py"
)
_main = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_main)

DALE, JESS = 1, 2


@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    path = tmp_path / "stockdaddy_members.db"
    shutil.copyfile(_REAL_DB, path)
    monkeypatch.setattr(Config, "DB_PATH", str(path))
    return path


@pytest.fixture
def client(fresh_db):
    return _main.app.test_client()


def _insert(path, sql, params=()):
    conn = sqlite3.connect(path)
    cursor = conn.execute(sql, params)
    conn.commit()
    conn.close()
    return cursor.lastrowid


def _add_person(path, email="person@example.com"):
    return _insert(
        path,
        "INSERT INTO owners (first_name, last_name, email, password_hash) "
        "VALUES ('Pat', 'Person', ?, 'x')",
        (email,),
    )


def _add_second_business(path):
    """A different company with its own owner, to prove businesses stay apart."""
    boss = _add_person(path, "boss@other.example")
    business = _insert(path, "INSERT INTO business (name, owner_id) VALUES ('Other Co', ?)", (boss,))
    member = _insert(
        path,
        "INSERT INTO business_member (business_id, owner_id, role) VALUES (?, ?, 'owner')",
        (business, boss),
    )
    return boss, business, member


def assert_error(response, status, text):
    assert response.status_code == status
    assert text in response.get_json()["error"]


# ---- list -----------------------------------------------------------------

def test_owner_can_list_members(client):
    response = client.get(f"/businesses/1/members?user_id={DALE}")
    assert response.status_code == 200
    assert [(m["owner_id"], m["role"]) for m in response.get_json()] == [
        (DALE, "owner"),
        (JESS, "employee"),
    ]


def test_employee_can_list_members(client):
    assert client.get(f"/businesses/1/members?user_id={JESS}").status_code == 200


def test_list_needs_a_user_id(client):
    assert_error(client.get("/businesses/1/members"), 400, "user_id is required")
    assert_error(client.get("/businesses/1/members?user_id=abc"), 400, "whole number")


def test_stranger_cannot_list_members(client, fresh_db):
    stranger = _add_person(fresh_db)
    assert_error(client.get(f"/businesses/1/members?user_id={stranger}"), 404, "Business not found")


def test_other_business_owner_cannot_see_this_business(client, fresh_db):
    boss, other_business, _ = _add_second_business(fresh_db)
    assert_error(client.get(f"/businesses/1/members?user_id={boss}"), 404, "Business not found")
    # ...but can see their own.
    assert client.get(f"/businesses/{other_business}/members?user_id={boss}").status_code == 200


# ---- add ------------------------------------------------------------------

def test_owner_can_add_an_employee(client, fresh_db):
    person = _add_person(fresh_db)
    response = client.post(
        "/businesses/1/members", json={"user_id": DALE, "owner_id": person, "role": "employee"}
    )
    assert response.status_code == 201
    assert response.get_json()["owner_id"] == person
    assert response.get_json()["role"] == "employee"
    assert client.get(f"/businesses/1/members?user_id={person}").status_code == 200


def test_employee_cannot_add_members(client, fresh_db):
    person = _add_person(fresh_db)
    response = client.post(
        "/businesses/1/members", json={"user_id": JESS, "owner_id": person, "role": "employee"}
    )
    assert_error(response, 403, "owner role is required")


def test_stranger_cannot_add_members(client, fresh_db):
    stranger = _add_person(fresh_db)
    response = client.post(
        "/businesses/1/members", json={"user_id": stranger, "owner_id": stranger, "role": "owner"}
    )
    assert_error(response, 404, "Business not found")


def test_add_checks_the_body(client):
    assert_error(client.post("/businesses/1/members", json={}), 400, "user_id is required")
    body = {"user_id": DALE, "owner_id": 5, "role": "boss"}
    assert_error(client.post("/businesses/1/members", json=body), 400, "role must be")


def test_add_same_person_twice_is_409(client):
    body = {"user_id": DALE, "owner_id": JESS, "role": "employee"}
    assert_error(client.post("/businesses/1/members", json=body), 409, "already exists")


def test_add_unknown_person_is_409_and_next_write_works(client, fresh_db):
    body = {"user_id": DALE, "owner_id": 999999, "role": "employee"}
    assert_error(client.post("/businesses/1/members", json=body), 409, "doesn't exist")
    person = _add_person(fresh_db)
    ok = client.post(
        "/businesses/1/members", json={"user_id": DALE, "owner_id": person, "role": "employee"}
    )
    assert ok.status_code == 201


# ---- change role ----------------------------------------------------------

def test_owner_can_promote_an_employee(client):
    response = client.put("/businesses/1/members/2", json={"user_id": DALE, "role": "owner"})
    assert response.status_code == 200
    assert response.get_json()["role"] == "owner"


def test_employee_cannot_change_roles(client):
    response = client.put("/businesses/1/members/2", json={"user_id": JESS, "role": "owner"})
    assert_error(response, 403, "owner role is required")


def test_cannot_demote_the_last_owner(client):
    response = client.put("/businesses/1/members/1", json={"user_id": DALE, "role": "employee"})
    assert_error(response, 409, "at least one owner")


def test_can_demote_an_owner_when_another_owner_remains(client):
    client.put("/businesses/1/members/2", json={"user_id": DALE, "role": "owner"})
    response = client.put("/businesses/1/members/1", json={"user_id": JESS, "role": "employee"})
    assert response.status_code == 200
    assert response.get_json()["role"] == "employee"


def test_change_role_checks_the_role_value(client):
    response = client.put("/businesses/1/members/2", json={"user_id": DALE, "role": "boss"})
    assert_error(response, 400, "role must be")


def test_change_role_unknown_member_is_404(client):
    response = client.put("/businesses/1/members/999999", json={"user_id": DALE, "role": "owner"})
    assert_error(response, 404, "Member not found")


def test_cannot_change_a_member_of_another_business(client, fresh_db):
    _, _, other_member = _add_second_business(fresh_db)
    response = client.put(
        f"/businesses/1/members/{other_member}", json={"user_id": DALE, "role": "employee"}
    )
    assert_error(response, 404, "Member not found")


# ---- remove ---------------------------------------------------------------

def test_owner_can_remove_an_employee_and_they_lose_access(client):
    assert client.delete(f"/businesses/1/members/2?user_id={DALE}").status_code == 204
    assert_error(client.get(f"/businesses/1/members?user_id={JESS}"), 404, "Business not found")


def test_employee_cannot_remove_members(client):
    assert_error(client.delete(f"/businesses/1/members/2?user_id={JESS}"), 403, "owner role")


def test_cannot_remove_the_last_owner(client):
    assert_error(client.delete(f"/businesses/1/members/1?user_id={DALE}"), 409, "at least one owner")


def test_remove_unknown_member_is_404(client):
    assert_error(client.delete(f"/businesses/1/members/999999?user_id={DALE}"), 404, "Member not found")


def test_cannot_remove_a_member_of_another_business(client, fresh_db):
    _, _, other_member = _add_second_business(fresh_db)
    response = client.delete(f"/businesses/1/members/{other_member}?user_id={DALE}")
    assert_error(response, 404, "Member not found")


def test_remove_needs_a_user_id(client):
    assert_error(client.delete("/businesses/1/members/2"), 400, "user_id is required")
    
    
    
# ---- creating a business makes its creator the first owner ----------------

def test_creating_a_business_makes_the_creator_an_owner(client, fresh_db):
    person = _add_person(fresh_db)
    created = client.post("/businesses", json={"name": "New Roofing Co", "owner_id": person})
    assert created.status_code == 201
    business_id = created.get_json()["business_id"]

    members = client.get(f"/businesses/{business_id}/members?user_id={person}")
    assert members.status_code == 200
    assert [(m["owner_id"], m["role"]) for m in members.get_json()] == [(person, "owner")]


def test_a_new_owner_can_build_a_team_right_away(client, fresh_db):
    boss = _add_person(fresh_db, "boss2@example.com")
    helper = _add_person(fresh_db, "helper@example.com")
    business_id = client.post(
        "/businesses", json={"name": "Fresh Co", "owner_id": boss}
    ).get_json()["business_id"]

    added = client.post(
        f"/businesses/{business_id}/members",
        json={"user_id": boss, "owner_id": helper, "role": "employee"},
    )
    assert added.status_code == 201


def test_a_refused_business_leaves_nothing_behind(client, fresh_db):
    before = client.get(f"/businesses?user_id={DALE}").get_json()
    refused = client.post("/businesses", json={"name": "Ghost Co", "owner_id": 999999})
    assert refused.status_code == 409
    assert client.get(f"/businesses?user_id={DALE}").get_json() == before
    assert len(client.get(f"/businesses/1/members?user_id={DALE}").get_json()) == 2  
    
    
def _add_by_email(client, email, user_id=DALE, role="employee"):
    return client.post(
        "/businesses/1/members", json={"user_id": user_id, "email": email, "role": role}
    )


def test_owner_can_add_an_employee_by_email(client, fresh_db):
    person = _add_person(fresh_db, "pat@example.com")
    response = _add_by_email(client, "pat@example.com")
    assert response.status_code == 201
    assert response.get_json()["owner_id"] == person
    assert response.get_json()["role"] == "employee"
    assert client.get(f"/businesses/1/members?user_id={person}").status_code == 200


def test_email_is_matched_ignoring_case_and_spaces(client, fresh_db):
    person = _add_person(fresh_db, "pat@example.com")
    response = _add_by_email(client, "  PAT@Example.COM ")
    assert response.status_code == 201
    assert response.get_json()["owner_id"] == person


def test_adding_an_unknown_email_is_404_and_next_write_works(client, fresh_db):
    assert_error(_add_by_email(client, "nobody@nowhere.example"), 404, "No account found with that email")
    _add_person(fresh_db, "pat@example.com")
    assert _add_by_email(client, "pat@example.com").status_code == 201


def test_send_either_email_or_owner_id_but_not_both(client, fresh_db):
    person = _add_person(fresh_db, "pat@example.com")
    neither = client.post("/businesses/1/members", json={"user_id": DALE, "role": "employee"})
    assert_error(neither, 400, "either email or owner_id")
    both = client.post(
        "/businesses/1/members",
        json={"user_id": DALE, "email": "pat@example.com", "owner_id": person, "role": "employee"},
    )
    assert_error(both, 400, "either email or owner_id")


def test_only_an_owner_can_add_by_email_and_it_does_not_reveal_which_emails_exist(client, fresh_db):
    _add_person(fresh_db, "pat@example.com")
    assert_error(_add_by_email(client, "pat@example.com", user_id=JESS), 403, "owner role is required")
    # An employee gets the same answer whether or not the email exists.
    assert_error(_add_by_email(client, "nobody@nowhere.example", user_id=JESS), 403, "owner role is required")
    stranger = _add_person(fresh_db, "stranger@example.com")
    assert_error(_add_by_email(client, "pat@example.com", user_id=stranger), 404, "Business not found")


def test_adding_the_same_email_twice_is_409(client):
    assert_error(_add_by_email(client, "crew@prairieroofing.example"), 409, "already exists")    