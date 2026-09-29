"""
Owner filter tests (NF-REQ-12): a logged-in owner only ever sees their own
businesses, buildings, items and compliance rows.

Owner 1 is the seeded account and owns all the seed data. Each test registers
a second, empty owner on a private copy of the database and checks that none
of owner 1's data leaks to them, both from db.py and through the real routes.
"""

import pytest

import db
from app import app

OWNER = 1


@pytest.fixture
def other_owner(fresh_db):
    return db.register_owner("Other", "Owner", "other@example.com", "password123")


@pytest.fixture
def client_as(other_owner):
    """A test client logged in as the second owner."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess["user"] = "Other"
            sess["owner_id"] = other_owner
        yield client


# --- db.py -----------------------------------------------------------------

def test_other_owner_sees_no_businesses(other_owner):
    assert db.get_dashboard_hierarchy(other_owner) == []


def test_other_owner_cannot_open_seeded_building(other_owner):
    assert db.get_building(other_owner, 1) is None
    assert db.get_building(OWNER, 1) is not None


def test_other_owner_sees_no_items(other_owner):
    assert db.get_items(other_owner) == []


def test_other_owner_cannot_open_seeded_item(other_owner):
    assert db.get_item_detail(other_owner, 1) is None
    assert db.get_item_detail(OWNER, 1) is not None


def test_other_owner_sees_no_compliance_rows(other_owner):
    assert db.get_compliance_report(other_owner) == []


def test_in_transit_item_still_belongs_to_its_owner():
    # The In Transit item has no storage_id; it's traced back to its owner
    # through its last movement, so it must still show up for owner 1.
    in_transit = [i for i in db.get_items(OWNER) if i["status"] == "In Transit"]
    assert len(in_transit) == 1
    assert db.get_item_detail(OWNER, in_transit[0]["id"]) is not None


# --- routes ----------------------------------------------------------------

def test_logged_out_user_is_sent_to_login():
    app.config["TESTING"] = True
    with app.test_client() as client:
        for path in ["/dashboard", "/building/1", "/items", "/items/1", "/compliance"]:
            resp = client.get(path)
            assert resp.status_code == 302
            assert "/login" in resp.headers["Location"]


def test_other_owner_is_bounced_from_seeded_building(client_as):
    resp = client_as.get("/building/1")
    assert resp.status_code == 302
    assert "/dashboard" in resp.headers["Location"]


def test_other_owner_is_bounced_from_seeded_item(client_as):
    resp = client_as.get("/items/1")
    assert resp.status_code == 302
    assert "/items" in resp.headers["Location"]


def test_other_owner_dashboard_is_empty(client_as):
    html = client_as.get("/dashboard").get_data(as_text=True)
    assert "Prairie Roofing" not in html
    assert "No businesses yet" in html


def test_other_owner_items_page_is_empty(client_as):
    html = client_as.get("/items").get_data(as_text=True)
    assert "Nail Gun #1" not in html
