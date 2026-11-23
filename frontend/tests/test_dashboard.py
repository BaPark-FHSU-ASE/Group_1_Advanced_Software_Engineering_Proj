"""The Dashboard and its business and building buttons, against a fake API."""

from tests import sample_data
from tests.conftest import page_text


def _html(client, path="/dashboard"):
    return page_text(client.get(path))


def test_dashboard_reads_the_report_for_the_logged_in_user(client, api):
    html = _html(client)
    assert api.called("get_dashboard") == [(1,)]
    assert "Prairie Roofing" in html
    assert "Hays — 100 Main St" in html and "Salina — 9 Elm Ave" in html


def test_building_cards_have_summary_counts(client, api):
    html = _html(client)
    assert "1 room · 2 storage units · 3 items" in html
    assert "1 shortage" in html
    assert "Empty — open to add rooms" in html  # Salina


def test_owner_sees_owner_buttons(client, api):
    html = _html(client)
    assert "+ Building" in html and "Rename" in html and "Yes, retire this business" in html


def test_employee_sees_no_owner_buttons(employee, api):
    api.returns["get_dashboard"] = sample_data.dashboard(role="employee")
    html = _html(employee)
    assert "+ Building" not in html
    assert "Rename" not in html
    assert "retire" not in html.lower()
    assert "employee" in html  # role shown next to the business name


def test_dashboard_refreshes_role_in_session(employee, api):
    # Promoted to owner since logging in.
    _html(employee)
    with employee.session_transaction() as sess:
        assert sess["is_owner"] is True


def test_empty_dashboard(client, api):
    api.returns["get_dashboard"] = []
    assert "No businesses yet" in _html(client)


def test_add_business(client, api):
    api.returns["add_business"] = {"business_id": 9, "name": "Acme"}
    resp = client.post("/businesses", data={"name": " Acme "}, follow_redirects=True)
    assert api.called("add_business") == [(1, "Acme")]
    assert 'Added business "Acme".' in page_text(resp)


def test_blank_business_name_is_left_to_the_api(client, api):
    api.fail("add_business", 400, "name is required")
    resp = client.post("/businesses", data={"name": ""}, follow_redirects=True)
    assert api.called("add_business") == [(1, "")]
    assert "name is required" in page_text(resp)


def test_rename_business(client, api):
    api.returns["rename_business"] = {"business_id": 1, "name": "Prairie Roofing Co"}
    resp = client.post("/businesses/1/rename", data={"name": "Prairie Roofing Co"},
                       follow_redirects=True)
    assert api.called("rename_business") == [(1, 1, "Prairie Roofing Co")]
    assert "Renamed business to" in page_text(resp)


def test_retire_business(client, api):
    api.returns["retire_business"] = {"business_id": 1, "name": "Prairie Roofing"}
    resp = client.post("/businesses/1/retire", follow_redirects=True)
    assert api.called("retire_business") == [(1, 1)]
    assert 'Retired "Prairie Roofing".' in page_text(resp)


def test_retire_business_with_buildings_shows_why(client, api):
    api.fail("retire_business", 409, "Can't retire this business: 2 buildings still inside")
    resp = client.post("/businesses/1/retire", follow_redirects=True)
    assert "2 buildings still inside" in page_text(resp)


def test_employee_action_refused_by_api_is_shown(employee, api):
    api.fail("rename_business", 403, "The owner role is required")
    resp = employee.post("/businesses/1/rename", data={"name": "X"}, follow_redirects=True)
    assert "The owner role is required" in page_text(resp)


def test_add_building_opens_it_with_room_form(client, api):
    resp = client.post("/businesses/1/buildings", data={
        "street_address": "1 New Rd", "city": "Hays", "state": "Kansas"})
    assert api.called("add_building") == [(1, 1, "1 New Rd", "Hays", "Kansas")]
    assert resp.location.endswith("/building/3?add=room")


def test_someone_elses_business_goes_back_to_dashboard(client, api):
    api.fail("add_building", 404, "Business not found")
    resp = client.post("/businesses/99/buildings", data={
        "street_address": "x", "city": "y", "state": "z"})
    assert resp.location.endswith("/dashboard")
