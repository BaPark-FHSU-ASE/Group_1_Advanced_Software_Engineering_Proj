"""
Tests for db.update_item_status() and the POST /items/<id>/status route
(REQ-11, REQ-12).

Seed items used: 1 is In Storage (storage 1), 4 is In Use (storage 1),
92 is In Transit (no storage). All belong to owner 1.
"""

import pytest

import db
from app import app

OWNER = 1
OTHER_OWNER = 999999


@pytest.fixture(autouse=True)
def _isolated(fresh_db):
    """Every test here writes, so each gets its own copy of the database."""


def _item_row(item_id):
    conn = db.get_connection()
    try:
        return conn.execute(
            "SELECT item_status, storage_id FROM item WHERE item_id = ?", (item_id,)
        ).fetchone()
    finally:
        conn.close()


def _last_movement(item_id):
    conn = db.get_connection()
    try:
        return conn.execute(
            "SELECT * FROM item_movement WHERE item_id = ? "
            "ORDER BY item_movement_id DESC LIMIT 1",
            (item_id,),
        ).fetchone()
    finally:
        conn.close()


def _movement_count(item_id):
    conn = db.get_connection()
    try:
        return conn.execute(
            "SELECT COUNT(*) FROM item_movement WHERE item_id = ?", (item_id,)
        ).fetchone()[0]
    finally:
        conn.close()


def test_storage_to_in_use_logs_status_only():
    assert db.update_item_status(OWNER, 1, "In Use") is True
    row = _item_row(1)
    assert row["item_status"] == "In Use"
    assert row["storage_id"] == 1  # didn't move
    m = _last_movement(1)
    assert (m["from_status"], m["to_status"]) == ("In Storage", "In Use")
    assert m["from_storage_id"] is None and m["to_storage_id"] is None


def test_going_in_transit_leaves_storage():
    db.update_item_status(OWNER, 4, "In Transit")
    row = _item_row(4)
    assert row["item_status"] == "In Transit"
    assert row["storage_id"] is None
    m = _last_movement(4)
    assert m["from_storage_id"] == 1 and m["to_storage_id"] is None
    assert (m["from_status"], m["to_status"]) == ("In Use", "In Transit")


def test_in_transit_item_still_listed_for_owner():
    db.update_item_status(OWNER, 1, "In Transit")
    ids = [i["id"] for i in db.get_items(OWNER)]
    assert 1 in ids


def test_arriving_needs_a_destination():
    with pytest.raises(ValueError):
        db.update_item_status(OWNER, 92, "In Storage")
    assert _item_row(92)["item_status"] == "In Transit"


def test_arriving_sets_storage():
    db.update_item_status(OWNER, 92, "In Storage", storage_id=2)
    row = _item_row(92)
    assert row["item_status"] == "In Storage"
    assert row["storage_id"] == 2
    m = _last_movement(92)
    assert m["from_storage_id"] is None and m["to_storage_id"] == 2


def test_same_status_changes_nothing():
    before = _movement_count(1)
    assert db.update_item_status(OWNER, 1, "In Storage") is False
    assert _movement_count(1) == before


def test_unknown_status_rejected():
    with pytest.raises(ValueError):
        db.update_item_status(OWNER, 1, "Lost")


def test_other_owner_cannot_change_status():
    with pytest.raises(db.NotFoundOrNotOwned):
        db.update_item_status(OTHER_OWNER, 1, "In Use")
    assert _item_row(1)["item_status"] == "In Storage"


def test_status_change_shows_in_history():
    db.update_item_status(OWNER, 1, "In Use")
    history = db.get_item_detail(OWNER, 1)["movement_history"]
    assert history[0]["status_change"] == "In Storage → In Use"


# --- route -----------------------------------------------------------------

def _client(owner_id):
    app.config["TESTING"] = True
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user"] = "Test"
        sess["owner_id"] = owner_id
    return client


def test_route_changes_status_and_redirects_back():
    resp = _client(OWNER).post("/items/1/status", data={"status": "In Use"})
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/items/1")
    assert _item_row(1)["item_status"] == "In Use"


def test_route_ignores_other_owner():
    resp = _client(OTHER_OWNER).post("/items/1/status", data={"status": "In Use"})
    assert resp.status_code == 302
    assert _item_row(1)["item_status"] == "In Storage"


def test_item_page_shows_status_buttons():
    html = _client(OWNER).get("/items/1").get_data(as_text=True)
    assert "Change Status" in html
    assert 'value="In Use"' in html
    assert "✓ In Storage" in html
