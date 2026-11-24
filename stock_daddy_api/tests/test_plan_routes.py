"""
Tests for POST /plans (REQ-18 to REQ-22, REQ-24, REQ-27).

The seed data is the same five-building problem as instance B in
Optimizer/instances.py, so the plan from the real database has to come out
at instance B's known costs. That's the end-to-end check that the
database -> optimizer -> JSON path is right.
"""

import json
import shutil

import pytest

from app.config import Config
from tests.conftest import _REAL_DB
from tests.route_helpers import *  # noqa: F403  (DALE, JESS, load_app, run_sql, ...)

app = load_app("stock_daddy_api_main_plan_routes")

INSTANCE_B_OPTIMAL = 575.44
INSTANCE_B_BASELINE = 1072.19
TOL = 0.01

# every key frontend/API_CONTRACT.md says the page reads
CONTRACT_KEYS = {
    "generated", "no_shortages", "optimal", "gap", "total_cost", "transfer_cost",
    "acquisition_cost", "greedy_cost", "trips", "acquisitions", "shortage_costs",
}


@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    path = tmp_path / "stockdaddy_plan_routes.db"
    shutil.copyfile(_REAL_DB, path)
    monkeypatch.setattr(Config, "DB_PATH", str(path))
    return path


@pytest.fixture
def client(fresh_db):
    return app.test_client()


def run_plan(client, user_id=DALE):
    return client.post("/plans", json={"user_id": user_id})


@pytest.fixture
def plan(client):
    response = run_plan(client)
    assert response.status_code == 200
    return response.get_json()


# --- the plan itself -----------------------------------------------------

def test_seed_data_gives_instance_b_costs(plan):
    assert abs(plan["total_cost"] - INSTANCE_B_OPTIMAL) < TOL
    assert abs(plan["greedy_cost"] - INSTANCE_B_BASELINE) < TOL
    assert plan["optimal"] is True and plan["gap"] == pytest.approx(0.0)
    assert plan["method"] == "milp_optimal"
    assert len(plan["trips"]) == 3


def test_response_has_every_field_the_frontend_reads(plan):
    assert CONTRACT_KEYS <= set(plan)
    trip = plan["trips"][0]
    assert {"from", "to", "items", "dispatch_cost", "handling_cost"} <= set(trip)
    assert {"qty", "type"} <= set(trip["items"][0])


def test_trip_and_purchase_costs_add_up_to_the_total(plan):
    trips = sum(t["dispatch_cost"] + t["handling_cost"] for t in plan["trips"])
    bought = sum(a["cost"] for a in plan["acquisitions"])
    assert abs(trips + bought - plan["total_cost"]) < TOL
    assert abs(plan["transfer_cost"] + plan["acquisition_cost"] - plan["total_cost"]) < TOL


def test_buildings_and_types_are_shown_by_name(plan):
    labels = {t["from"] for t in plan["trips"]} | {t["to"] for t in plan["trips"]}
    # the two Salina buildings get their street added so they can be told apart
    assert "Salina (458 N Ohio Street)" in labels
    assert not any(label.isdigit() for label in labels)


# --- REQ-21: cost per shortage -------------------------------------------

def test_shortage_costs_add_up_to_the_plan_total_to_the_cent(plan):
    total = sum(row["cost"] for row in plan["shortage_costs"])
    assert round(total, 2) == round(plan["total_cost"], 2)


def test_each_shortage_row_covers_the_whole_shortage(plan, fresh_db):
    shortage_units = one_value(
        fresh_db, "SELECT SUM(shortage_qty) FROM v_building_item_type_position"
    )
    assert sum(row["qty"] for row in plan["shortage_costs"]) == shortage_units
    for row in plan["shortage_costs"]:
        assert row["cost_per_unit"] == pytest.approx(row["cost"] / row["qty"], abs=0.01)


# --- REQ-22: the actual items on each truck ------------------------------

def test_each_item_row_names_exactly_qty_items(plan):
    for trip in plan["trips"]:
        for row in trip["items"]:
            assert len(row["item_ids"]) == len(row["names"]) == row["qty"]


def test_no_item_is_on_two_trucks(plan):
    picked = [i for t in plan["trips"] for row in t["items"] for i in row["item_ids"]]
    assert len(picked) == len(set(picked))


def test_picked_items_are_in_storage_at_the_origin_and_the_right_type(plan, fresh_db):
    for trip in plan["trips"]:
        for row in trip["items"]:
            for item_id in row["item_ids"]:
                status, kind, city, retired = run_query(fresh_db, item_id)
                assert status == "In Storage" and retired is None
                assert kind == row["type"]
                assert trip["from"].startswith(city)


def test_items_in_use_are_never_picked(client, fresh_db):
    first = run_plan(client).get_json()
    item_id = first["trips"][0]["items"][0]["item_ids"][0]
    run_sql(fresh_db, "UPDATE item SET item_status = 'In Use' WHERE item_id = ?", (item_id,))

    second = run_plan(client).get_json()
    picked = {i for t in second["trips"] for row in t["items"] for i in row["item_ids"]}
    assert item_id not in picked


# --- retired buildings, access, errors -----------------------------------

def test_retired_building_is_left_out_of_the_plan(client, fresh_db):
    building_id = add_empty_building(fresh_db)
    hard_hat = one_value(fresh_db, "SELECT item_type_id FROM item_type WHERE name = 'Hard Hat'")
    run_sql(fresh_db, "INSERT INTO target_quantity (building_id, item_type_id, target_qty) "
                      "VALUES (?, ?, 2)", (building_id, hard_hat))

    before = {row["building"] for row in run_plan(client).get_json()["shortage_costs"]}
    assert "Hays (1 Empty St)" in before

    run_sql(fresh_db, "UPDATE building SET retired = CURRENT_TIMESTAMP WHERE building_id = ?",
            (building_id,))
    after = {row["building"] for row in run_plan(client).get_json()["shortage_costs"]}
    assert not any(label.startswith("Hays (") for label in after)


def test_employee_cannot_run_a_plan(client):
    assert_error(run_plan(client, user_id=JESS), 403, "owner role is required")


def test_plan_needs_a_user_id(client):
    assert_error(client.post("/plans", json={}), 400, "user_id is required")


def test_someone_with_no_business_gets_an_empty_plan(client, fresh_db):
    stranger = add_person(fresh_db)
    plan = run_plan(client, user_id=stranger).get_json()
    assert plan["no_shortages"] is True
    assert plan["trips"] == [] and plan["shortage_costs"] == []


def test_shortage_nobody_can_fill_is_a_409_that_says_which(client, fresh_db):
    scaffold = run_sql(fresh_db, "INSERT INTO item_type (name) VALUES ('Scaffold')")
    run_sql(fresh_db, "INSERT INTO target_quantity (building_id, item_type_id, target_qty) "
                      "VALUES (1, ?, 2)", (scaffold,))
    response = run_plan(client)
    assert response.status_code == 409
    message = response.get_json()["error"]
    assert "Scaffold" in message and "Salina (458 N Ohio Street)" in message


# --- REQ-27: saved runs --------------------------------------------------

def test_each_run_is_saved_to_plan_run(client, fresh_db):
    before = one_value(fresh_db, "SELECT COUNT(*) FROM plan_run")
    plan = run_plan(client).get_json()
    assert one_value(fresh_db, "SELECT COUNT(*) FROM plan_run") == before + 1

    run_by, method, total, baseline, saved = run_sql_row(
        fresh_db,
        "SELECT run_by, method, total_cost, baseline_cost, plan_json "
        "FROM plan_run WHERE plan_run_id = ?",
        (plan["plan_run_id"],),
    )
    assert run_by == DALE and method == "milp_optimal"
    assert abs(total - INSTANCE_B_OPTIMAL) < TOL and abs(baseline - INSTANCE_B_BASELINE) < TOL
    assert json.loads(saved)["trips"] == plan["trips"]


# --- small helpers just for this file ------------------------------------

def run_query(path, item_id):
    return run_sql_row(
        path,
        "SELECT i.item_status, t.name, b.city, i.retired FROM item i "
        "JOIN item_type t ON t.item_type_id = i.item_type_id "
        "JOIN storage s ON s.storage_id = i.storage_id "
        "JOIN room r ON r.room_id = s.room_id "
        "JOIN building b ON b.building_id = r.building_id "
        "WHERE i.item_id = ?",
        (item_id,),
    )


def run_sql_row(path, sql, params=()):
    import sqlite3
    conn = sqlite3.connect(path)
    row = conn.execute(sql, params).fetchone()
    conn.close()
    return row
