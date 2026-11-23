"""The Item Types page (REQ-9), against a fake API."""

from tests.conftest import page_text


def test_lists_types_with_cost_and_service_life(client, api):
    text = page_text(client.get("/item-types"))
    assert api.called("get_item_types") == [(1,)]
    assert "Ladder" in text and "24 ft" in text and "$300.00" in text
    assert "730 days" in text and "No limit" in text


def test_owner_sees_add_edit_delete(client, api):
    text = page_text(client.get("/item-types"))
    assert "+ Add Item Type" in text and "Yes, delete Ladder" in text
    html = client.get("/item-types").get_data(as_text=True)
    assert 'value="730"' in html  # edit form is filled in


def test_employee_only_views(employee, api):
    text = page_text(employee.get("/item-types"))
    assert "Ladder" in text
    assert "+ Add Item Type" not in text and "Delete" not in text and "Edit" not in text


def test_add_item_type_with_blanks_as_not_set(client, api):
    api.returns["add_item_type"] = {"item_type_id": 9, "name": "Drill"}
    resp = client.post("/item-types", data={"name": " Drill ", "description": "",
                                            "replacement_cost": "", "service_life_days": ""},
                       follow_redirects=True)
    assert api.called("add_item_type") == [(1, {"name": "Drill", "description": None,
                                                "replacement_cost": None,
                                                "service_life_days": None})]
    assert 'Added item type "Drill".' in page_text(resp)


def test_edit_item_type_sends_numbers(client, api):
    api.returns["update_item_type"] = {"item_type_id": 2, "name": "Ladder"}
    client.post("/item-types/2/edit", data={"name": "Ladder", "description": "28 ft",
                                            "replacement_cost": "325.50",
                                            "service_life_days": "1825"})
    assert api.called("update_item_type") == [(1, 2, {"name": "Ladder", "description": "28 ft",
                                                      "replacement_cost": 325.5,
                                                      "service_life_days": 1825})]


def test_delete_in_use_type_shows_api_reason(client, api):
    api.fail("delete_item_type", 409, "That record refers to something that doesn't exist, "
                                      "or other records still depend on it")
    resp = client.post("/item-types/1/delete",
                       headers={"Referer": "http://localhost/item-types"}, follow_redirects=True)
    assert "other records still depend on it" in page_text(resp)


def test_employee_refused_by_api(employee, api):
    api.fail("add_item_type", 403, "The owner role is required")
    resp = employee.post("/item-types", data={"name": "X"}, follow_redirects=True)
    assert "The owner role is required" in page_text(resp)
