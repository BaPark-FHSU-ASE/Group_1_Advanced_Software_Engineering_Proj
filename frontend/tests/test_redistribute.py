"""
Tests for the optimizer hookup: db.get_optimizer_inputs(), redistribution.py,
and the /redistribute route (REQ-18, REQ-19, REQ-20, REQ-24, NF-REQ-8, NF-REQ-12).

The seed data is the same five-site problem as Optimizer/instances.py's
instance B, so the plan built from the live database has to reproduce that
instance's pre-solved costs. That is the end-to-end check that the
database -> optimizer translation is right.
"""

import pytest

import db
import redistribution
from app import app
from Optimizer.instances import INSTANCE_B_NEAREST_SOURCE_COST, INSTANCE_B_OPTIMAL_COST

OWNER = 1
OTHER_OWNER = 999999
TOL = 0.01  # costs come from SQLite REAL columns


def _client(owner_id=OWNER):
    app.config["TESTING"] = True
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user"] = "Test"
        sess["owner_id"] = owner_id
    return client


# --- db.get_optimizer_inputs ------------------------------------------------

def test_inputs_cover_all_five_buildings_and_twenty_routes():
    inputs = db.get_optimizer_inputs(OWNER)
    assert len(inputs["buildings"]) == 5
    assert len(inputs["routes"]) == 20
    assert len(inputs["item_types"]) == 6


def test_two_salina_buildings_get_distinct_labels():
    labels = [b["label"] for b in db.get_optimizer_inputs(OWNER)["buildings"]]
    assert len(set(labels)) == len(labels)
    assert sum(label.startswith("Salina (") for label in labels) == 2
    assert "Hays" in labels


def test_hays_nail_gun_shortage_comes_through():
    inputs = db.get_optimizer_inputs(OWNER)
    hays = next(b["id"] for b in inputs["buildings"] if b["label"] == "Hays")
    nail_gun = next(t["id"] for t in inputs["item_types"] if t["name"] == "Nail Gun")
    row = next(p for p in inputs["positions"]
               if p["building_id"] == hays and p["item_type_id"] == nail_gun)
    assert row["demand"] == 2


def test_other_owner_gets_no_data():
    inputs = db.get_optimizer_inputs(OTHER_OWNER)
    assert inputs["buildings"] == []
    assert inputs["routes"] == []
    assert inputs["positions"] == []


# --- redistribution.generate_plan -------------------------------------------

def test_plan_matches_instance_b_optimum():
    plan = redistribution.generate_plan(OWNER)
    assert plan["generated"] and plan["optimal"]
    assert plan["total_cost"] == pytest.approx(INSTANCE_B_OPTIMAL_COST, abs=TOL)


def test_baseline_matches_instance_b_nearest_source():
    plan = redistribution.generate_plan(OWNER)
    assert plan["greedy_cost"] == pytest.approx(INSTANCE_B_NEAREST_SOURCE_COST, abs=TOL)


def test_trip_and_purchase_costs_add_up_to_total():
    plan = redistribution.generate_plan(OWNER)
    trips = sum(t["dispatch_cost"] + t["handling_cost"] for t in plan["trips"])
    buys = sum(a["cost"] for a in plan["acquisitions"])
    assert trips == pytest.approx(plan["transfer_cost"], abs=TOL)
    assert buys == pytest.approx(plan["acquisition_cost"], abs=TOL)
    assert trips + buys == pytest.approx(plan["total_cost"], abs=TOL)


def test_plan_uses_display_names_not_ids():
    plan = redistribution.generate_plan(OWNER)
    trip = plan["trips"][0]
    assert not trip["from"].isdigit()
    assert all(not item["type"].isdigit() for item in trip["items"])
    # Instance B's optimum buys 2 hard hats at Abilene instead of shipping them.
    assert any(a["building"] == "Abilene" and a["type"] == "Hard Hat" and a["qty"] == 2
               for a in plan["acquisitions"])


def test_owner_with_nothing_short_gets_empty_plan():
    plan = redistribution.generate_plan(OTHER_OWNER)
    assert plan["no_shortages"]
    assert plan["trips"] == []


# --- /redistribute route ----------------------------------------------------

def test_get_requires_login():
    app.config["TESTING"] = True
    resp = app.test_client().get("/redistribute")
    assert resp.status_code == 302


def test_get_shows_empty_state_without_running():
    resp = _client().get("/redistribute")
    assert resp.status_code == 200
    assert b"No plan generated yet" in resp.data


def test_post_runs_optimizer_and_shows_plan():
    resp = _client().post("/redistribute", follow_redirects=True)
    assert resp.status_code == 200
    assert b"$575.44" in resp.data
    assert b"Recommended Trips" in resp.data
    assert b"Buy New Instead" in resp.data
    assert b"Plan generated at" in resp.data


def test_post_redirects_so_refresh_does_not_resubmit():
    resp = _client().post("/redistribute")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/redistribute")


def test_plan_stays_after_leaving_and_coming_back():
    client = _client()
    client.post("/redistribute")
    client.get("/dashboard")
    resp = client.get("/redistribute")
    assert b"$575.44" in resp.data
    assert b"No plan generated yet" not in resp.data


def test_logout_clears_saved_plan():
    client = _client()
    client.post("/redistribute")
    client.get("/logout")
    with client.session_transaction() as sess:
        sess["user"] = "Test"
        sess["owner_id"] = OWNER
    resp = client.get("/redistribute")
    assert b"No plan generated yet" in resp.data


def test_saved_plan_is_per_session():
    _client().post("/redistribute")
    resp = _client().get("/redistribute")  # a different browser/session
    assert b"No plan generated yet" in resp.data
