"""Setting stock targets from the building page (REQ-15).

The first tests use the fake API. The end-to-end tests at the bottom start
the real API (see real_api in conftest.py) against a private copy of the
database, since PUT /target_quantities already exists.
"""

import sqlite3

import pytest

from tests.conftest import logged_in_client, needs_api, page_text


def _flashes(client):
    with client.session_transaction() as sess:
        return sess.get("_flashes", [])


def test_set_target_calls_the_api(client, api):
    api.returns["set_target"] = ({}, False)
    resp = client.post("/building/1/targets", data={"item_type_id": "1", "target_qty": "8"})
    assert api.called("set_target") == [(1, 1, 1, 8)]
    assert resp.location.endswith("/building/1")
    assert _flashes(client) == [("success", "Updated the Nail Gun target to 8.")]


def test_new_target_says_set(client, api):
    client.post("/building/1/targets", data={"item_type_id": "2", "target_qty": "1"})
    assert _flashes(client) == [("success", "Set the Ladder target to 1.")]


def test_missing_item_type_never_reaches_the_api(client, api):
    client.post("/building/1/targets", data={"target_qty": "3"})
    assert api.called("set_target") == []
    assert _flashes(client) == [("error", "Pick an item type.")]


def test_bad_quantity_is_left_to_the_api(client, api):
    api.fail("set_target", 400, "target_qty must be a whole number 0 or more")
    client.post("/building/1/targets", data={"item_type_id": "1", "target_qty": "-1"})
    assert api.called("set_target") == [(1, 1, 1, -1)]
    assert _flashes(client) == [("error", "target_qty must be a whole number 0 or more")]


def test_other_owners_building_redirects_to_dashboard(client, api):
    api.fail("set_target", 404, "Building not found")
    resp = client.post("/building/99/targets", data={"item_type_id": "1", "target_qty": "3"})
    assert resp.location.endswith("/dashboard")


def test_api_down_shows_a_message(client, api):
    api.unreachable("set_target")
    resp = client.post("/building/1/targets", data={"item_type_id": "1", "target_qty": "3"})
    assert resp.status_code == 503
    assert "Couldn't reach the Stock Daddy API" in page_text(resp)


def test_not_logged_in_redirects_to_login():
    from app import app
    resp = app.test_client().post("/building/1/targets",
                                  data={"item_type_id": "1", "target_qty": "8"})
    assert resp.headers["Location"].endswith("/login")


# --- End to end, through the real API ---------------------------------------

def _target(db_path, building_id, item_type_id):
    conn = sqlite3.connect(db_path)
    rows = conn.execute("SELECT target_qty FROM target_quantity "
                        "WHERE building_id = ? AND item_type_id = ?",
                        (building_id, item_type_id)).fetchall()
    conn.close()
    return [r[0] for r in rows]


@needs_api
def test_end_to_end_update_existing_target(real_api, fresh_db):
    client = logged_in_client()
    client.post("/building/1/targets", data={"item_type_id": "1", "target_qty": "9"})
    assert _flashes(client) == [("success", "Updated the Nail Gun target to 9.")]
    assert _target(fresh_db, 1, 1) == [9]  # updated, not duplicated


@needs_api
def test_end_to_end_new_target(real_api, fresh_db):
    conn = sqlite3.connect(fresh_db)
    item_type_id = conn.execute("INSERT INTO item_type (name) VALUES ('Test Drill')").lastrowid
    conn.commit()
    conn.close()
    client = logged_in_client()
    client.post("/building/1/targets", data={"item_type_id": str(item_type_id), "target_qty": "2"})
    assert _flashes(client) == [("success", "Set the Test Drill target to 2.")]
    assert _target(fresh_db, 1, item_type_id) == [2]


@needs_api
def test_end_to_end_other_owner_cannot_set_target(real_api, fresh_db):
    client = logged_in_client(user_id=999999)
    resp = client.post("/building/1/targets", data={"item_type_id": "1", "target_qty": "50"})
    assert resp.location.endswith("/dashboard")
    assert _target(fresh_db, 1, 1) != [50]
