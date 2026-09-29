"""
Tests for the Dashboard's + Add Business, + Building and Edit buttons:
db.add_business(), db.rename_business(), db.add_building() and their routes.
"""

import pytest

import db
from app import app

OWNER = 1
OTHER_OWNER = 999999


@pytest.fixture(autouse=True)
def _isolated(fresh_db):
    """Every test here writes, so each gets its own copy of the database."""


def _client(owner_id):
    app.config["TESTING"] = True
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user"] = "Test"
        sess["owner_id"] = owner_id
    return client


def test_add_business_shows_on_dashboard():
    db.add_business(OWNER, "Test Gutters LLC")
    names = [b["name"] for b in db.get_dashboard_hierarchy(OWNER)]
    assert "Test Gutters LLC" in names


def test_new_owner_can_add_their_first_business():
    new_owner = db.register_owner("New", "Owner", "new@example.com", "password123")
    db.add_business(new_owner, "Fresh Start Co")
    businesses = db.get_dashboard_hierarchy(new_owner)
    assert [b["name"] for b in businesses] == ["Fresh Start Co"]
    # ...and still can't see anyone else's
    assert "Prairie Roofing & Exteriors" not in [b["name"] for b in businesses]


def test_rename_business():
    db.rename_business(OWNER, 1, "Prairie Roofing Co")
    assert db.get_dashboard_hierarchy(OWNER)[0]["name"] == "Prairie Roofing Co"


def test_rename_rejects_other_owner():
    with pytest.raises(db.NotFoundOrNotOwned):
        db.rename_business(OTHER_OWNER, 1, "Hijacked")
    assert db.get_dashboard_hierarchy(OWNER)[0]["name"] == "Prairie Roofing & Exteriors"


def test_add_building_shows_under_business():
    building_id = db.add_building(OWNER, 1, "100 Main St", "Wichita", "KS")
    building = db.get_building(OWNER, building_id)
    assert building["address"] == "100 Main St, Wichita, KS"
    assert building["rooms"] == []


def test_add_building_rejects_other_owner():
    with pytest.raises(db.NotFoundOrNotOwned):
        db.add_building(OTHER_OWNER, 1, "1 Nowhere Rd", "Nowhere", "KS")


# --- routes ----------------------------------------------------------------

def test_add_business_route():
    resp = _client(OWNER).post("/businesses", data={"name": "Route Test Inc"})
    assert resp.status_code == 302
    assert "Route Test Inc" in [b["name"] for b in db.get_dashboard_hierarchy(OWNER)]


def test_add_business_route_requires_name():
    before = len(db.get_dashboard_hierarchy(OWNER))
    _client(OWNER).post("/businesses", data={"name": "   "})
    assert len(db.get_dashboard_hierarchy(OWNER)) == before


def test_add_building_route_opens_new_building_with_room_form():
    resp = _client(OWNER).post(
        "/businesses/1/buildings",
        data={"street_address": "5 Elm St", "city": "Topeka", "state": "KS"},
    )
    assert resp.status_code == 302
    assert "/building/" in resp.headers["Location"]
    assert "add=room" in resp.headers["Location"]


def test_dashboard_buttons_are_real_forms():
    html = _client(OWNER).get("/dashboard").get_data(as_text=True)
    assert 'href="#"' not in html
    assert 'action="/businesses"' in html
    assert 'action="/businesses/1/buildings"' in html
    assert 'action="/businesses/1/rename"' in html
