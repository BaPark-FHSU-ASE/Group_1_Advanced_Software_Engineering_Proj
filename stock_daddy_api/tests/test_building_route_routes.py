
import json
import shutil

import pytest

from app.config import Config
from tests.conftest import _REAL_DB
from tests.route_helpers import *  # noqa: F403  (DALE, JESS, load_app, run_sql, ...)

app = load_app("stock_daddy_api_main_building_route_routes")

GOOD = {"distance_miles": 12.5, "fixed_dispatch_cost": 80, "cost_per_unit_mile": 0.04}


@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    path = tmp_path / "stockdaddy_building_route_routes.db"
    shutil.copyfile(_REAL_DB, path)
    monkeypatch.setattr(Config, "DB_PATH", str(path))
    return path


@pytest.fixture
def client(fresh_db):
    return app.test_client()


def _add_building(path, business_id=1, city="Newton", street="1 Main St"):
    return run_sql(
        path,
        "INSERT INTO building (business_id, state, city, street_address) VALUES (?, 'Kansas', ?, ?)",
        (business_id, city, street),
    )


def _other_business(path):
    """A second company with its own owner and two buildings. -> (person, [building ids])"""
    person = add_person(path, "boss@other.example")
    business = run_sql(path, "INSERT INTO business (name, owner_id) VALUES ('Other Co', ?)", (person,))
    run_sql(path, "INSERT INTO business_member (business_id, owner_id, role) VALUES (?, ?, 'owner')", (business, person))
    return person, business, [_add_building(path, business, "Wichita", "5 Elm"), _add_building(path, business, "Topeka", "9 Oak")]


def _post(client, from_id, to_id, user_id=DALE, **costs):
    body = {"user_id": user_id, "from_building_id": from_id, "to_building_id": to_id}
    body.update(GOOD)
    body.update(costs)
    return client.post("/routes", json=body)


def _edit(client, route_id, user_id=DALE, **costs):
    body = {"user_id": user_id}
    body.update(GOOD)
    body.update(costs)
    return client.put(f"/routes/{route_id}", json=body)


def _route_count(path):
    return one_value(path, "SELECT COUNT(*) FROM building_route")



def test_members_see_their_routes_with_labels_and_costs(client):
    for user in (DALE, JESS):
        response = client.get(f"/routes?user_id={user}")
        assert response.status_code == 200
        routes = response.get_json()
        assert len(routes) == 20
        assert set(routes[0]) == {
            "route_id", "from_building_id", "from_label", "to_building_id", "to_label",
            "distance_miles", "fixed_dispatch_cost", "cost_per_unit_mile", "handling_cost_per_unit",
        }

    first, second = client.get(f"/routes?user_id={DALE}").get_json()[:2]
    assert first == {
        "route_id": 1, "from_building_id": 1, "from_label": "Salina (458 N Ohio Street)",
        "to_building_id": 2, "to_label": "Salina (900 S Broadway Blvd)",
        "distance_miles": 9.2, "fixed_dispatch_cost": 71.04, "cost_per_unit_mile": 0.05,
        "handling_cost_per_unit": 0.46,
    }
    # Abilene is the only building in its city, so it needs no street.
    assert (second["to_label"], second["handling_cost_per_unit"]) == ("Abilene", 1.23)


def test_a_stranger_sees_no_routes_and_the_user_id_is_required(client, fresh_db):
    stranger = add_person(fresh_db)
    assert client.get(f"/routes?user_id={stranger}").get_json() == []
    assert_error(client.get("/routes"), 400, "user_id is required")


def test_each_business_sees_only_its_own_routes(client, fresh_db):
    boss, _, (wichita, topeka) = _other_business(fresh_db)
    run_sql(
        fresh_db,
        "INSERT INTO building_route (from_building_id, to_building_id, distance_miles, fixed_dispatch_cost, cost_per_unit_mile) "
        "VALUES (?, ?, 30, 90, 0.05)", (wichita, topeka),
    )
    theirs = client.get(f"/routes?user_id={boss}").get_json()
    assert [(r["from_label"], r["to_label"]) for r in theirs] == [("Wichita", "Topeka")]
    assert len(client.get(f"/routes?user_id={DALE}").get_json()) == 20


def test_a_route_joining_a_business_you_are_not_in_is_not_shown_to_either_side(client, fresh_db):
    boss, _, (wichita, _) = _other_business(fresh_db)
    run_sql(
        fresh_db,
        "INSERT INTO building_route (from_building_id, to_building_id, distance_miles, fixed_dispatch_cost, cost_per_unit_mile) "
        "VALUES (1, ?, 200, 300, 0.05)", (wichita,),
    )
    assert len(client.get(f"/routes?user_id={DALE}").get_json()) == 20
    assert client.get(f"/routes?user_id={boss}").get_json() == []


def test_routes_to_a_retired_building_are_left_out(client, fresh_db):
    run_sql(fresh_db, "UPDATE building SET retired = CURRENT_TIMESTAMP WHERE building_id = 3")
    expected = one_value(
        fresh_db, "SELECT COUNT(*) FROM building_route WHERE from_building_id <> 3 AND to_building_id <> 3"
    )
    routes = client.get(f"/routes?user_id={DALE}").get_json()
    assert len(routes) == expected == 12
    assert all(3 not in (r["from_building_id"], r["to_building_id"]) for r in routes)


def test_two_buildings_in_one_city_get_their_streets_only_when_needed(client, fresh_db):
    _add_building(fresh_db, 1, "Abilene", "77 Second St")
    labels = {}
    for route in client.get(f"/routes?user_id={DALE}").get_json():
        labels[route["from_building_id"]] = route["from_label"]
    assert labels[3] == "Abilene (1204 NW 3rd Street)"
    assert labels[4] == "Hays"


def test_an_owner_can_add_a_route_and_gets_it_back_with_labels(client, fresh_db):
    new_building = _add_building(fresh_db)
    before = _route_count(fresh_db)
    response = _post(client, 1, new_building)
    assert response.status_code == 201
    route = response.get_json()
    assert (route["from_label"], route["to_label"]) == ("Salina (458 N Ohio Street)", "Newton")
    assert (route["distance_miles"], route["fixed_dispatch_cost"], route["cost_per_unit_mile"]) == (12.5, 80, 0.04)
    assert route["handling_cost_per_unit"] == 0.5
    assert _route_count(fresh_db) == before + 1
    assert route["route_id"] in [r["route_id"] for r in client.get(f"/routes?user_id={JESS}").get_json()]


def test_each_direction_is_its_own_route_but_not_twice(client, fresh_db):
    new_building = _add_building(fresh_db)
    assert _post(client, 1, new_building).status_code == 201
    assert _post(client, new_building, 1).status_code == 201
    again = _post(client, 1, new_building)
    assert_error(again, 409, "There is already a route from Salina (458 N Ohio Street) to Newton.")
    assert _post(client, 1, 2).status_code == 409


def test_zero_distance_and_zero_rate_are_allowed_but_not_a_zero_dispatch_cost(client, fresh_db):
    new_building = _add_building(fresh_db)
    assert _post(client, 1, new_building, distance_miles=0, cost_per_unit_mile=0).status_code == 201
    other = _add_building(fresh_db, city="Larned", street="3 Pine")
    assert_error(_post(client, 1, other, fixed_dispatch_cost=0), 400, "Dispatch cost must be more than 0.")


def test_adding_says_what_is_wrong_in_plain_sentences(client, fresh_db):
    new_building = _add_building(fresh_db)
    before = _route_count(fresh_db)
    assert_error(_post(client, 1, 1), 400, "Choose two different buildings.")
    assert_error(
        client.post("/routes", json={"user_id": DALE, "from_building_id": 1, "to_building_id": new_building}),
        400, "Distance in miles is required. Dispatch cost is required. Cost per unit mile is required.",
    )
    assert_error(
        _post(client, 1, new_building, distance_miles=-1, fixed_dispatch_cost=-5, cost_per_unit_mile=-0.1),
        400, "Distance in miles must be 0 or more. Dispatch cost must be more than 0. Cost per unit mile must be 0 or more.",
    )
    assert_error(_post(client, 1, new_building, distance_miles="far"), 400, "distance_miles must be a number")
    nan = client.post(
        "/routes", content_type="application/json",
        data=json.dumps({"user_id": DALE, "from_building_id": 1, "to_building_id": new_building,
                         "fixed_dispatch_cost": 80, "cost_per_unit_mile": 0.04}).replace("}", ', "distance_miles": NaN}'),
    )
    assert_error(nan, 400, "Distance in miles must be a number.")
    assert_error(client.post("/routes", data="hello"), 400, "Request body must be a JSON object")
    assert _route_count(fresh_db) == before


def test_only_an_owner_of_both_buildings_can_add_a_route(client, fresh_db):
    new_building = _add_building(fresh_db)
    assert_error(_post(client, 1, new_building, user_id=JESS), 403, "owner role is required")

    boss, _, (wichita, _) = _other_business(fresh_db)
    assert_error(_post(client, 1, new_building, user_id=boss), 404, "Building not found")
    assert_error(_post(client, wichita, new_building, user_id=boss), 404, "Building not found")
    assert_error(_post(client, 1, 999999), 404, "Building not found")
    assert_error(_post(client, 999999, 1), 404, "Building not found")


def test_cannot_add_a_route_to_a_retired_building(client, fresh_db):
    retired = _add_building(fresh_db)
    run_sql(fresh_db, "UPDATE building SET retired = CURRENT_TIMESTAMP WHERE building_id = ?", (retired,))
    before = _route_count(fresh_db)
    assert_error(_post(client, 1, retired), 409, "That building is retired")
    assert_error(_post(client, retired, 1), 409, "That building is retired")
    assert _route_count(fresh_db) == before


def test_an_owner_can_change_a_routes_costs_and_the_buildings_stay_put(client):
    response = _edit(client, 1, distance_miles=10, fixed_dispatch_cost=80, cost_per_unit_mile=0.06)
    assert response.status_code == 200
    route = response.get_json()
    assert (route["route_id"], route["from_building_id"], route["to_building_id"]) == (1, 1, 2)
    assert (route["distance_miles"], route["fixed_dispatch_cost"], route["cost_per_unit_mile"]) == (10, 80, 0.06)
    assert route["handling_cost_per_unit"] == 0.6
    assert route["from_label"] == "Salina (458 N Ohio Street)"
    assert client.get(f"/routes?user_id={JESS}").get_json()[0]["distance_miles"] == 10


def test_changing_a_route_checks_the_numbers_and_changes_nothing_if_they_are_wrong(client):
    assert_error(_edit(client, 1, fixed_dispatch_cost=0), 400, "Dispatch cost must be more than 0.")
    assert_error(client.put("/routes/1", json={"user_id": DALE}), 400, "Distance in miles is required.")
    assert client.get(f"/routes?user_id={DALE}").get_json()[0]["fixed_dispatch_cost"] == 71.04


def test_only_an_owner_can_change_a_route_and_strangers_cannot_find_it(client, fresh_db):
    assert_error(_edit(client, 1, user_id=JESS), 403, "owner role is required")
    boss, _, _ = _other_business(fresh_db)
    assert_error(_edit(client, 1, user_id=boss), 404, "Route not found")
    assert_error(_edit(client, 999999), 404, "Route not found")
    assert client.get(f"/routes?user_id={DALE}").get_json()[0]["fixed_dispatch_cost"] == 71.04



def test_an_owner_can_delete_a_route(client, fresh_db):
    assert client.delete(f"/routes/1?user_id={DALE}").status_code == 204
    assert _route_count(fresh_db) == 19
    assert 1 not in [r["route_id"] for r in client.get(f"/routes?user_id={DALE}").get_json()]
    assert_error(client.delete(f"/routes/1?user_id={DALE}"), 404, "Route not found")


def test_only_an_owner_can_delete_a_route_and_strangers_cannot_find_it(client, fresh_db):
    assert_error(client.delete(f"/routes/1?user_id={JESS}"), 403, "owner role is required")
    boss, _, _ = _other_business(fresh_db)
    assert_error(client.delete(f"/routes/1?user_id={boss}"), 404, "Route not found")
    assert_error(client.delete("/routes/1"), 400, "user_id is required")
    assert _route_count(fresh_db) == 20