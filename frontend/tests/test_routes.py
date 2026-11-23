"""The Route Costs page (REQ-17), against a fake API."""

from tests import sample_data
from tests.conftest import page_text


def test_lists_routes(client, api):
    text = page_text(client.get("/routes"))
    assert api.called("get_routes") == [(1,)]
    assert "Hays" in text and "Salina" in text
    assert "98.0 mi" in text and "$75.00" in text and "$0.1200" in text and "$11.76" in text


def test_owner_can_add_between_owned_buildings(client, api):
    text = page_text(client.get("/routes"))
    assert "+ Add Route" in text
    assert "Hays — 100 Main St" in text and "Salina — 9 Elm Ave" in text


def test_employee_only_views(employee, api):
    api.returns["get_dashboard"] = sample_data.dashboard(role="employee")
    text = page_text(employee.get("/routes"))
    assert "Hays" in text
    assert "+ Add Route" not in text and "Edit" not in text and "Delete" not in text


def test_one_building_means_nothing_to_route(client, api):
    api.returns["get_routes"] = []
    api.returns["get_dashboard"] = [dict(sample_data.dashboard()[0],
                                         buildings=[sample_data.HAYS])]
    text = page_text(client.get("/routes"))
    assert "+ Add Route" not in text and "Add a second building first." in text


def test_add_route(client, api):
    api.returns["add_route"] = dict(sample_data.ROUTES[0], route_id=2)
    resp = client.post("/routes", data={
        "from_building_id": "2", "to_building_id": "1", "distance_miles": "98",
        "fixed_dispatch_cost": "75", "cost_per_unit_mile": "0.12"}, follow_redirects=True)
    assert api.called("add_route") == [(1, 2, 1, 98.0, 75.0, 0.12)]
    assert "Added the route Hays → Salina." in page_text(resp)


def test_add_route_bad_values_show_api_message(client, api):
    api.fail("add_route", 400, "That value is not allowed (chk_route_distinct)")
    resp = client.post("/routes", data={
        "from_building_id": "1", "to_building_id": "1", "distance_miles": "1",
        "fixed_dispatch_cost": "1", "cost_per_unit_mile": "1"},
        headers={"Referer": "http://localhost/routes"}, follow_redirects=True)
    assert "chk_route_distinct" in page_text(resp)


def test_edit_route(client, api):
    api.returns["update_route"] = sample_data.ROUTES[0]
    client.post("/routes/1/edit", data={"distance_miles": "100", "fixed_dispatch_cost": "80",
                                        "cost_per_unit_mile": "0.1"})
    assert api.called("update_route") == [(1, 1, 100.0, 80.0, 0.1)]


def test_delete_route(client, api):
    resp = client.post("/routes/1/delete")
    assert api.called("delete_route") == [(1, 1)]
    assert resp.location.endswith("/routes")
