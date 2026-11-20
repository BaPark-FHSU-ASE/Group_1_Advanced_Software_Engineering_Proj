import shutil
import sqlite3

import pytest
from flask import Flask, jsonify

from app.Validation_Helper import register_error_handlers
from app.access import AccessError, require_record_role, require_role
from app.config import Config
from tests.conftest import _REAL_DB



@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    path = tmp_path / "stockdaddy_fresh.db"
    shutil.copyfile(_REAL_DB, path)
    monkeypatch.setattr(Config, "DB_PATH", str(path))
    return path


def _add_stranger(path):
    conn = sqlite3.connect(path)
    cursor = conn.execute(
        "INSERT INTO owners (first_name, last_name, email, password_hash) "
        "VALUES ('Some', 'Stranger', 'stranger@example.com', 'x')"
    )
    conn.commit()
    conn.close()
    return cursor.lastrowid


def test_owner_passes_owner_check(fresh_db):
    assert require_role(1, 1, "owner") == "owner"


def test_owner_passes_employee_check(fresh_db):
    assert require_role(1, 1, "employee") == "owner"


def test_employee_passes_employee_check(fresh_db):
    assert require_role(2, 1, "employee") == "employee"


def test_role_defaults_to_employee(fresh_db):
    assert require_role(2, 1) == "employee"


def test_employee_cannot_do_owner_things(fresh_db):
    with pytest.raises(AccessError) as caught:
        require_role(2, 1, "owner")
    assert caught.value.status_code == 403
    assert "owner role is required" in caught.value.message


def test_stranger_gets_404(fresh_db):
    stranger = _add_stranger(fresh_db)
    with pytest.raises(AccessError) as caught:
        require_role(stranger, 1, "employee")
    assert caught.value.status_code == 404


def test_unknown_business_looks_the_same_as_not_yours(fresh_db):
    stranger = _add_stranger(fresh_db)
    with pytest.raises(AccessError) as not_yours:
        require_role(stranger, 1, "employee")
    with pytest.raises(AccessError) as missing:
        require_role(1, 999999, "employee")
    assert (not_yours.value.status_code, not_yours.value.message) == (
        missing.value.status_code,
        missing.value.message,
    )


def test_missing_user_id_gets_404(fresh_db):
    with pytest.raises(AccessError) as caught:
        require_role(None, 1, "employee")
    assert caught.value.status_code == 404


def test_unknown_role_name_is_a_programming_error(fresh_db):
    with pytest.raises(ValueError):
        require_role(1, 1, "manager")


def test_removing_someone_takes_their_access_away(fresh_db):
    from app.repositories import business_member_repository

    assert require_role(2, 1, "employee") == "employee"
    business_member_repository.remove(2)
    with pytest.raises(AccessError):
        require_role(2, 1, "employee")


def test_access_errors_become_json_responses(fresh_db):
    """AccessError rides the existing handlers: JSON body, right status code."""
    app = Flask(__name__)
    register_error_handlers(app)

    @app.route("/check/<int:user_id>/<role>")
    def check(user_id, role):
        return jsonify({"role": require_role(user_id, 1, role)})

    client = app.test_client()
    assert client.get("/check/1/owner").get_json() == {"role": "owner"}

    denied = client.get("/check/2/owner")
    assert denied.status_code == 403
    assert denied.get_json() == {"error": "The owner role is required"}

    hidden = client.get("/check/999/owner")
    assert hidden.status_code == 404
    assert hidden.get_json() == {"error": "Business not found"}
    

def test_the_not_found_message_can_be_customised(fresh_db):
    stranger = _add_stranger(fresh_db)
    with pytest.raises(AccessError) as caught:
        require_role(stranger, 1, "owner", not_found="Building not found")
    assert (caught.value.status_code, caught.value.message) == (404, "Building not found")    

def test_record_role_follows_the_record_to_its_business(fresh_db):
    assert require_record_role("building", 1, 1, "owner") == "owner"
    assert require_record_role("room", 1, 2) == "employee"

    with pytest.raises(AccessError) as caught:
        require_record_role("storage", 1, 2, "owner")
    assert (caught.value.status_code, caught.value.message) == (403, "The owner role is required")


def test_missing_and_not_yours_records_give_the_same_404(fresh_db):
    stranger = _add_stranger(fresh_db)
    answers = []
    for record_id in (1, 999999):
        with pytest.raises(AccessError) as caught:
            require_record_role("room", record_id, stranger)
        answers.append((caught.value.status_code, caught.value.message))
    assert answers == [(404, "Room not found")] * 2    