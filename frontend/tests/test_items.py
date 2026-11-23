"""The item list, adding items, and an item's page, against a fake API."""

from tests import sample_data
from tests.conftest import page_text


def _flashes(client):
    with client.session_transaction() as sess:
        return sess.get("_flashes", [])


# --- List ---------------------------------------------------------------------

def test_items_page_lists_items_with_flags(client, api):
    text = page_text(client.get("/items"))
    assert api.called("get_items") == [(1,)]
    assert "Nail Gun #1" in text and "Nail Gun #2" in text
    assert "In transit" in text
    assert "Past service life" in text
    assert "1 item is past its item type's service life." in text


def test_items_page_empty(client, api):
    api.returns["get_items"] = []
    text = page_text(client.get("/items"))
    assert "No items found." in text and "past its item type" not in text


# --- Adding items (REQ-6, REQ-14) ---------------------------------------------

def test_add_form_lists_types_and_storage(client, api):
    text = page_text(client.get("/items/new?storage_id=2"))
    assert "Ladder" in text and "Nail Gun" in text
    assert "Tool Room / Shelf" in text
    html = client.get("/items/new?storage_id=2").get_data(as_text=True)
    assert '<option value="2" selected>' in html


def test_add_form_without_storage_points_to_dashboard(client, api):
    api.returns["get_storage_choices"] = []
    assert "add a room and a storage unit first" in page_text(client.get("/items/new"))


def test_add_one_item_opens_it(client, api):
    resp = client.post("/items/new", data={"storage_id": "1", "item_type_id": "1",
                                           "quantity": "1", "name": " Big Gun "})
    assert api.called("add_items") == [(1, 1, 1, 1, "Big Gun")]
    assert resp.location.endswith("/items/10")
    assert _flashes(client) == [("success", "Added 1 item.")]


def test_add_several_goes_to_list(client, api):
    api.returns["add_items"] = [10, 11, 12]
    resp = client.post("/items/new", data={"storage_id": "1", "item_type_id": "1",
                                           "quantity": "3"})
    assert api.called("add_items") == [(1, 1, 1, 3, "")]
    assert resp.location.endswith("/items")
    assert _flashes(client) == [("success", "Added 3 items.")]


def test_add_error_keeps_form_and_shows_api_message(client, api):
    api.fail("add_items", 400, "quantity must be between 1 and 100")
    resp = client.post("/items/new", data={"storage_id": "1", "item_type_id": "1",
                                           "quantity": "500", "name": "Keep me"})
    text = page_text(resp)
    assert resp.status_code == 200
    assert "quantity must be between 1 and 100" in text
    assert 'value="Keep me"' in resp.get_data(as_text=True)


def test_add_to_someone_elses_storage(client, api):
    api.fail("add_items", 404, "Storage not found")
    text = page_text(client.post("/items/new", data={"storage_id": "99", "item_type_id": "1",
                                                     "quantity": "1"}))
    assert "That storage unit or item type wasn't found." in text


# --- Item page ----------------------------------------------------------------

def test_item_page_shows_details_and_history(client, api):
    text = page_text(client.get("/items/1"))
    assert api.called("get_item_detail") == [(1, 1)]
    assert "Nail Gun #1" in text and "2024-01-02" in text
    assert "Hays / Tool Room / Locker" in text


def test_item_page_shows_service_life_flag(client, api):
    api.returns["get_item_detail"] = sample_data.item_detail(expired=True)
    text = page_text(client.get("/items/1"))
    assert "Past service life" in text
    assert "30 days past its type's service life" in text


def test_someone_elses_item_goes_to_dashboard(client, api):
    api.fail("get_item_detail", 404, "Item not found")
    assert client.get("/items/99").location.endswith("/dashboard")


def test_in_transit_item_offers_destinations(client, api):
    api.returns["get_item_detail"] = sample_data.item_detail(status="In Transit")
    text = page_text(client.get("/items/1"))
    assert "Arrived at" in text and "Tool Room / Shelf" in text
    assert "Save Item" not in text  # can't edit while it has no storage unit


def test_owner_sees_edit_and_retire(client, api):
    text = page_text(client.get("/items/1"))
    assert "Save Item" in text and "Yes, retire this item" in text


def test_employee_can_change_status_but_not_edit(employee, api):
    api.returns["get_item_detail"] = sample_data.item_detail(role="employee")
    text = page_text(employee.get("/items/1"))
    assert "Change Status" in text and "In Use" in text
    assert "Save Item" not in text and "retire" not in text.lower()
    assert api.called("get_item_types") == []


# --- Status change (REQ-11, REQ-12) ---------------------------------------------

def test_status_change_goes_through_status_endpoint(client, api):
    resp = client.post("/items/1/status", data={"status": "In Use"})
    assert api.called("change_item_status") == [(1, 1, "In Use", None)]
    assert api.called("update_item") == []  # never the PUT, which skips history
    assert resp.location.endswith("/items/1")
    assert _flashes(client) == [("success", "Marked as In Use.")]


def test_arrival_sends_destination(client, api):
    client.post("/items/2/status", data={"status": "In Storage", "storage_id": "2"})
    assert api.called("change_item_status") == [(1, 2, "In Storage", 2)]


def test_unchanged_status_flashes_nothing(client, api):
    api.returns["change_item_status"] = False
    client.post("/items/1/status", data={"status": "In Storage"})
    assert _flashes(client) == []


def test_missing_destination_shows_api_message(client, api):
    api.fail("change_item_status", 400, "Choose where the item arrived.")
    resp = client.post("/items/2/status", data={"status": "In Storage"},
                       headers={"Referer": "http://localhost/items/2"})
    assert resp.location == "http://localhost/items/2"
    assert _flashes(client) == [("error", "Choose where the item arrived.")]


# --- Edit and retire ------------------------------------------------------------

def test_edit_keeps_location_and_status(client, api):
    resp = client.post("/items/1/edit", data={"name": "Gun A", "item_type_id": "2"})
    assert api.called("update_item") == [(1, 1, 2, 1, "In Storage", "Gun A")]
    assert resp.location.endswith("/items/1")


def test_retire_item(client, api):
    resp = client.post("/items/1/retire")
    assert api.called("retire_item") == [(1, 1)]
    assert resp.location.endswith("/items")
