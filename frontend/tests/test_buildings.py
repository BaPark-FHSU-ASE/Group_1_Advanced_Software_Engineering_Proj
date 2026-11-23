"""A building's page: rooms, storage units, edit and retire, floor view,
and a storage unit's own page. All against a fake API."""

from tests import sample_data
from tests.conftest import page_text


def test_building_page_reads_report(client, api):
    text = page_text(client.get("/building/1"))
    assert api.called("get_building_report") == [(1, 1)]
    assert "Hays — 100 Main St" in text
    assert "Tool Room" in text and "Locker" in text
    assert "-2 shortage" in text and "Balanced" in text


def test_someone_elses_building_goes_to_dashboard(client, api):
    api.fail("get_building_report", 404, "Building not found")
    resp = client.get("/building/99")
    assert resp.status_code == 302 and resp.location.endswith("/dashboard")


def test_owner_sees_edit_retire_and_add_controls(client, api):
    text = page_text(client.get("/building/1"))
    for control in ["+ Add Room", "Save Building", "Yes, retire this building",
                    "+ Storage Unit", "Yes, retire this room", "Set Target"]:
        assert control in text, control


def test_employee_sees_no_owner_controls(employee, api):
    api.returns["get_building_report"] = sample_data.building_report(role="employee")
    text = page_text(employee.get("/building/1"))
    for control in ["+ Add Room", "Save Building", "retire", "+ Storage Unit", "Set Target"]:
        assert control not in text, control
    # Adding items is allowed for employees.
    assert "+ Items" in text
    assert api.called("get_item_types") == []


def test_add_room_form_opens_on_arrival(client, api):
    html = client.get("/building/1?add=room").get_data(as_text=True)
    assert '<details class="inline-form" open>' in html


def test_floor_view_shows_rooms_as_tiles(client, api):
    text = page_text(client.get("/building/1?view=floor"))
    assert "Floor View" in text
    assert "/storage/1" in client.get("/building/1?view=floor").get_data(as_text=True)
    assert "3 Locker" in text and "0 Shelf" in text


def test_edit_building(client, api):
    resp = client.post("/building/1/edit", data={
        "business_id": "1", "street_address": "101 Main St", "city": "Hays", "state": "Kansas"})
    assert api.called("update_building") == [(1, 1, 1, "101 Main St", "Hays", "Kansas")]
    assert resp.location.endswith("/building/1")


def test_retire_building_goes_to_dashboard(client, api):
    resp = client.post("/building/1/retire")
    assert api.called("retire_building") == [(1, 1)]
    assert resp.location.endswith("/dashboard")


def test_retire_building_with_rooms_shows_apis_reason(client, api):
    api.fail("retire_building", 409, "Can't retire this building: 1 room still inside")
    resp = client.post("/building/1/retire", headers={"Referer": "http://localhost/building/1"},
                       follow_redirects=True)
    assert "1 room still inside" in page_text(resp)


def test_add_room(client, api):
    resp = client.post("/building/1/rooms", data={"name": " Garage "}, follow_redirects=True)
    assert api.called("add_room") == [(1, 1, "Garage")]
    assert 'Added room "Garage".' in page_text(resp)


def test_add_room_blank_name_shows_api_message(client, api):
    api.fail("add_room", 400, "location is required")
    resp = client.post("/building/1/rooms", data={"name": ""},
                       headers={"Referer": "http://localhost/building/1"}, follow_redirects=True)
    assert "location is required" in page_text(resp)


def test_rename_room(client, api):
    api.returns["update_room"] = {"room_id": 1, "location": "Shop"}
    resp = client.post("/rooms/1/edit", data={"building_id": "1", "name": "Shop"})
    assert api.called("update_room") == [(1, 1, 1, "Shop")]
    assert resp.location.endswith("/building/1")


def test_retire_room(client, api):
    resp = client.post("/rooms/1/retire", data={"building_id": "1"})
    assert api.called("retire_room") == [(1, 1)]
    assert resp.location.endswith("/building/1")


def test_add_storage(client, api):
    resp = client.post("/rooms/1/storage", data={"building_id": "1", "storage_type": "Bin"},
                       follow_redirects=True)
    assert api.called("add_storage") == [(1, 1, "Bin")]
    assert 'Added storage unit "Bin".' in page_text(resp)


# --- Storage page (UI-REQ-2) -------------------------------------------------------

def test_storage_page_lists_items(client, api):
    text = page_text(client.get("/storage/1"))
    assert api.called("get_storage_report") == [(1, 1)]
    assert "Nail Gun #1" in text and "Ladder #1" in text
    assert "Past service life" in text  # REQ-23 flag on Nail Gun #1
    assert "+ Add Items Here" in text and "Yes, retire this storage unit" in text


def test_storage_page_hides_owner_controls_from_employee(employee, api):
    api.returns["get_storage_report"] = sample_data.storage_report(role="employee")
    text = page_text(employee.get("/storage/1"))
    assert "retire" not in text.lower() and "Save Storage Unit" not in text
    assert "+ Add Items Here" in text


def test_edit_storage(client, api):
    resp = client.post("/storage/1/edit", data={"room_id": "1", "storage_type": "Big Locker"})
    assert api.called("update_storage") == [(1, 1, 1, "Big Locker")]
    assert resp.location.endswith("/storage/1")


def test_retire_storage(client, api):
    resp = client.post("/storage/1/retire", data={"building_id": "1"})
    assert api.called("retire_storage") == [(1, 1)]
    assert resp.location.endswith("/building/1")
