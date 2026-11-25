import shutil
import sqlite3

import pytest

from app.config import Config
from app.repositories import building_route_repository as routes
from tests.conftest import _REAL_DB
from tests.route_helpers import add_person, one_value, run_sql


@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    path = tmp_path / "stockdaddy_building_route.db"
    shutil.copyfile(_REAL_DB, path)
    monkeypatch.setattr(Config, "DB_PATH", str(path))
    return path


def _add_building(path, business_id=1, city="Newton", street="1 Main St"):
    return run_sql(
        path,
        "INSERT INTO building (business_id, state, city, street_address) VALUES (?, 'Kansas', ?, ?)",
        (business_id, city, street),
    )


def test_get_visible_returns_the_routes_between_a_persons_businesses(fresh_db):
    assert [r.building_route_id for r in routes.get_visible(1)] == list(range(1, 21))
    assert len(routes.get_visible(2)) == 20
    assert routes.get_visible(add_person(fresh_db)) == []
    assert routes.get_visible(999999) == []


def test_get_visible_skips_routes_to_retired_buildings(fresh_db):
    run_sql(fresh_db, "UPDATE building SET retired = CURRENT_TIMESTAMP WHERE building_id = 5")
    found = routes.get_visible(1)
    assert len(found) == 12
    assert all(5 not in (r.from_building_id, r.to_building_id) for r in found)


def test_get_visible_by_id_only_finds_routes_the_person_can_see(fresh_db):
    route = routes.get_visible_by_id(1, 1)
    assert (route.from_building_id, route.to_building_id) == (1, 2)
    assert (route.distance_miles, route.fixed_dispatch_cost, route.cost_per_unit_mile) == (9.2, 71.04, 0.05)
    assert round(route.handling_cost_per_unit, 4) == 0.46
    assert routes.get_visible_by_id(add_person(fresh_db), 1) is None
    assert routes.get_visible_by_id(1, 999999) is None


def test_get_by_pair_finds_one_direction_only(fresh_db):
    assert routes.get_by_pair(1, 2).building_route_id == 1
    assert routes.get_by_pair(2, 1).building_route_id == 5
    newcomer = _add_building(fresh_db)
    assert routes.get_by_pair(1, newcomer) is None


def test_building_labels_use_the_city_and_add_the_street_only_when_two_share_a_city(fresh_db):
    labels = routes.building_labels(1)
    assert labels == {
        1: "Salina (458 N Ohio Street)", 2: "Salina (900 S Broadway Blvd)",
        3: "Abilene", 4: "Hays", 5: "Great Bend",
    }
    _add_building(fresh_db, 1, "Hays", "8 Fort St")
    assert routes.building_labels(1)[4] == "Hays (2815 Vine Street)"


def test_building_labels_leave_out_retired_buildings_and_other_businesses(fresh_db):
    run_sql(fresh_db, "UPDATE building SET retired = CURRENT_TIMESTAMP WHERE building_id = 2")
    outsider = add_person(fresh_db, "boss@other.example")
    business = run_sql(fresh_db, "INSERT INTO business (name, owner_id) VALUES ('Other Co', ?)", (outsider,))
    run_sql(fresh_db, "INSERT INTO business_member (business_id, owner_id, role) VALUES (?, ?, 'owner')", (business, outsider))
    _add_building(fresh_db, business, "Wichita", "5 Elm")

    mine = routes.building_labels(1)
    assert 2 not in mine
    assert mine[1] == "Salina"          # the other Salina building is retired, so no street is needed
    assert set(routes.building_labels(outsider).values()) == {"Wichita"}


def test_create_update_and_delete(fresh_db):
    newcomer = _add_building(fresh_db)
    made = routes.create(1, newcomer, 12.5, 80, 0.04)
    assert (made.from_building_id, made.to_building_id, made.distance_miles) == (1, newcomer, 12.5)
    assert round(made.handling_cost_per_unit, 4) == 0.5

    changed = routes.update(made.building_route_id, 20, 90, 0.05)
    assert (changed.from_building_id, changed.to_building_id) == (1, newcomer)
    assert (changed.distance_miles, changed.fixed_dispatch_cost, changed.cost_per_unit_mile) == (20, 90, 0.05)
    assert round(changed.handling_cost_per_unit, 4) == 1.0
    assert routes.update(999999, 1, 1, 1) is None

    assert routes.delete(made.building_route_id) is True
    assert routes.delete(made.building_route_id) is False


def test_the_database_itself_refuses_a_duplicate_pair_a_loop_and_a_free_dispatch(fresh_db):
    newcomer = _add_building(fresh_db)
    with pytest.raises(sqlite3.IntegrityError):
        routes.create(1, 2, 5, 50, 0.05)                 # already exists
    with pytest.raises(sqlite3.IntegrityError):
        routes.create(1, 1, 5, 50, 0.05)                 # building to itself
    with pytest.raises(sqlite3.IntegrityError):
        routes.create(1, newcomer, 5, 0, 0.05)           # dispatch cost must be more than 0
    assert one_value(fresh_db, "SELECT COUNT(*) FROM building_route") == 20