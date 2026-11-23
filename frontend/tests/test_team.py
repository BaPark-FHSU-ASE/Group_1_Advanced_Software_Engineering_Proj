"""The Team page: adding employees and changing roles, against a fake API."""

from tests import sample_data
from tests.conftest import page_text


def _flashes(client):
    with client.session_transaction() as sess:
        return sess.get("_flashes", [])


def test_dashboard_links_owners_to_team(client, employee, api):
    assert "/businesses/1/team" in client.get("/dashboard").get_data(as_text=True)
    api.returns["get_dashboard"] = sample_data.dashboard(role="employee")
    assert "/businesses/1/team" not in employee.get("/dashboard").get_data(as_text=True)


def test_team_page_lists_members(client, api):
    text = page_text(client.get("/businesses/1/team"))
    assert api.called("get_members") == [(1, 1)]
    assert "Dale Prairie (you)" in text and "Jess Crew" in text
    assert "crew@prairieroofing.example" in text
    assert "Make owner" in text and "Make employee" in text and "+ Add Person" in text


def test_members_without_names_fall_back_to_account_id(client, api):
    api.returns["get_members"] = [{"business_member_id": 3, "business_id": 1,
                                   "owner_id": 5, "role": "employee"}]
    assert "Account #5" in page_text(client.get("/businesses/1/team"))


def test_employee_sees_team_read_only(employee, api):
    api.returns["get_dashboard"] = sample_data.dashboard(role="employee")
    text = page_text(employee.get("/businesses/1/team"))
    assert "Jess Crew" in text
    assert "+ Add Person" not in text and "Make owner" not in text and "Remove" not in text


def test_not_a_member_goes_to_dashboard(client, api):
    resp = client.get("/businesses/99/team")
    assert resp.location.endswith("/dashboard")
    assert api.called("get_members") == []


def test_add_member_by_email(client, api):
    resp = client.post("/businesses/1/team", data={"email": " new@crew.example ",
                                                   "role": "employee"})
    assert api.called("add_member") == [(1, 1, "new@crew.example", "employee")]
    assert resp.location.endswith("/businesses/1/team")
    assert _flashes(client) == [("success", "Added new@crew.example to the team.")]


def test_add_unknown_email_shows_api_message(client, api):
    api.fail("add_member", 400, "No account found with that email")
    resp = client.post("/businesses/1/team", data={"email": "who@x.y", "role": "employee"},
                       headers={"Referer": "http://localhost/businesses/1/team"})
    assert resp.location.endswith("/businesses/1/team")
    assert _flashes(client) == [("error", "No account found with that email")]


def test_change_role(client, api):
    client.post("/businesses/1/team/2/role", data={"role": "owner"})
    assert api.called("change_member_role") == [(1, 1, 2, "owner")]


def test_cannot_remove_last_owner(client, api):
    api.fail("remove_member", 409, "A business needs at least one owner")
    client.post("/businesses/1/team/1/remove",
                headers={"Referer": "http://localhost/businesses/1/team"})
    assert _flashes(client) == [("error", "A business needs at least one owner")]


def test_remove_member(client, api):
    client.post("/businesses/1/team/2/remove")
    assert api.called("remove_member") == [(1, 1, 2)]
