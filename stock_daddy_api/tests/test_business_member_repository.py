
import shutil
import sqlite3

import pytest

from app.config import Config
from app.repositories import business_member_repository as members
from tests.conftest import _REAL_DB

# Seed data: business 1 has Dale (owner_id 1, owner) and Jess (owner_id 2, employee).


@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    """A private database copy per test, so writes can't leak between tests."""
    path = tmp_path / "stockdaddy_fresh.db"
    shutil.copyfile(_REAL_DB, path)
    monkeypatch.setattr(Config, "DB_PATH", str(path))
    return path


def _insert(path, sql, params=()):
    conn = sqlite3.connect(path)
    cursor = conn.execute(sql, params)
    conn.commit()
    conn.close()
    return cursor.lastrowid


def _add_owner(path, email="new@example.com"):
    return _insert(
        path,
        "INSERT INTO owners (first_name, last_name, email, password_hash) "
        "VALUES ('New', 'Person', ?, 'x')",
        (email,),
    )


def _add_business(path, owner_id):
    return _insert(
        path, "INSERT INTO business (name, owner_id) VALUES ('Second Co', ?)", (owner_id,)
    )


def test_get_all_returns_seeded_members(fresh_db):
    found = members.get_all()
    assert [(m.owner_id, m.role) for m in found] == [(1, "owner"), (2, "employee")]


def test_get_all_filters_by_business(fresh_db):
    other_owner = _add_owner(fresh_db)
    other_business = _add_business(fresh_db, other_owner)
    members.add(other_business, other_owner, "owner")

    assert len(members.get_all(business_id=1)) == 2
    only = members.get_all(business_id=other_business)
    assert [m.owner_id for m in only] == [other_owner]


def test_get_by_id_returns_member(fresh_db):
    assert members.get_by_id(1).to_dict() == {
        "business_member_id": 1,
        "business_id": 1,
        "owner_id": 1,
        "role": "owner",
    }


def test_get_by_id_missing_returns_none(fresh_db):
    assert members.get_by_id(999999) is None


def test_get_role(fresh_db):
    assert members.get_role(1, 1) == "owner"
    assert members.get_role(1, 2) == "employee"


def test_get_role_is_none_for_strangers_and_unknown_business(fresh_db):
    stranger = _add_owner(fresh_db)
    assert members.get_role(1, stranger) is None
    assert members.get_role(999999, 1) is None


def test_count_owners(fresh_db):
    assert members.count_owners(1) == 1
    members.update_role(2, "owner")
    assert members.count_owners(1) == 2
    assert members.count_owners(999999) == 0


def test_add_returns_new_member(fresh_db):
    person = _add_owner(fresh_db)
    member = members.add(1, person, "employee")
    assert member.business_member_id > 2
    assert (member.business_id, member.owner_id, member.role) == (1, person, "employee")
    assert members.get_role(1, person) == "employee"


def test_add_same_person_twice_is_refused(fresh_db):
    with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"):
        members.add(1, 2, "employee")


def test_add_unknown_role_is_refused(fresh_db):
    person = _add_owner(fresh_db)
    with pytest.raises(sqlite3.IntegrityError, match="chk_member_role"):
        members.add(1, person, "manager")


def test_add_unknown_owner_or_business_is_refused(fresh_db):
    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
        members.add(1, 999999, "employee")
    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
        members.add(999999, 1, "employee")


def test_a_refused_add_does_not_lock_the_database(fresh_db):
    person = _add_owner(fresh_db)
    with pytest.raises(sqlite3.IntegrityError):
        members.add(1, 2, "employee")
    assert members.add(1, person, "employee").role == "employee"


def test_update_role_changes_and_returns_member(fresh_db):
    member = members.update_role(2, "owner")
    assert member.role == "owner"
    assert members.get_role(1, 2) == "owner"


def test_update_role_missing_returns_none(fresh_db):
    assert members.update_role(999999, "owner") is None


def test_update_role_unknown_role_is_refused(fresh_db):
    with pytest.raises(sqlite3.IntegrityError, match="chk_member_role"):
        members.update_role(2, "manager")


def test_remove_deletes_member(fresh_db):
    assert members.remove(2) is True
    assert members.get_by_id(2) is None
    assert members.get_role(1, 2) is None


def test_remove_missing_returns_false(fresh_db):
    assert members.remove(999999) is False
    
def test_has_role_anywhere(fresh_db):
    assert members.has_role_anywhere(1) is True
    assert members.has_role_anywhere(1, "owner") is True
    assert members.has_role_anywhere(2) is True
    assert members.has_role_anywhere(2, "owner") is False
    assert members.has_role_anywhere(999999) is False    
    
def test_share_a_business(fresh_db):
    assert members.share_a_business(1, 2) is True
    assert members.share_a_business(2, 1) is True
    assert members.share_a_business(1, 999999) is False
    assert members.share_a_business(999999, 1) is False    
    

def test_get_memberships_lists_each_business_and_role(fresh_db):
    assert members.get_memberships(1) == [{"business_id": 1, "role": "owner"}]
    assert members.get_memberships(2) == [{"business_id": 1, "role": "employee"}]
    assert members.get_memberships(_add_owner(fresh_db)) == []


def test_get_memberships_skips_retired_businesses(fresh_db):
    second = _add_business(fresh_db, 1)
    members.add(second, 1, "owner")
    assert [m["business_id"] for m in members.get_memberships(1)] == [1, second]

    _insert(fresh_db, "UPDATE business SET retired = CURRENT_TIMESTAMP WHERE business_id = ?", (second,))
    assert [m["business_id"] for m in members.get_memberships(1)] == [1]    