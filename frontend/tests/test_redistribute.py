"""The Redistribute page, which asks the API for a plan (POST /plans)."""

from tests.conftest import logged_in_client, page_text


def test_get_requires_login():
    from app import app
    resp = app.test_client().get("/redistribute")
    assert "/login" in resp.location


def test_get_shows_empty_state_without_running(client, api):
    text = page_text(client.get("/redistribute"))
    assert "No plan generated yet." in text and "Run Optimizer" in text
    assert api.called("run_plan") == []


def test_post_runs_plan_and_redirects(client, api):
    resp = client.post("/redistribute")
    assert api.called("run_plan") == [(1,)]
    assert resp.status_code == 302 and resp.location.endswith("/redistribute")


def test_plan_shows_trips_savings_and_cost_per_shortage(client, api):
    client.post("/redistribute")
    text = page_text(client.get("/redistribute"))
    assert "Salina → Hays" in text and "2× Nail Gun" in text
    assert "$98.52" in text and "$21.48" in text  # total and savings vs $120 baseline
    assert "Cost per Shortage" in text and "$49.26" in text  # REQ-21


def test_plan_stays_after_leaving_and_coming_back(client, api):
    client.post("/redistribute")
    client.get("/items")
    assert "Recommended Trips" in page_text(client.get("/redistribute"))
    assert api.called("run_plan") == [(1,)]


def test_logout_clears_saved_plan(client, api):
    client.post("/redistribute")
    client.get("/logout")
    fresh = logged_in_client()
    assert "No plan generated yet." in page_text(fresh.get("/redistribute"))


def test_no_shortages(client, api):
    api.returns["run_plan"] = {"generated": True, "no_shortages": True, "trips": [],
                               "acquisitions": [], "total_cost": 0.0, "optimal": True}
    client.post("/redistribute")
    assert "Nothing needs to move" in page_text(client.get("/redistribute"))


def test_infeasible_plan_shows_apis_sentence(client, api):
    api.fail("run_plan", 409, "No plan could cover every shortage.")
    resp = client.post("/redistribute", follow_redirects=True)
    assert "No plan could cover every shortage." in page_text(resp)


def test_not_optimal_shows_gap(client, api):
    from tests import sample_data
    api.returns["run_plan"] = dict(sample_data.PLAN, optimal=False, gap=0.016)
    client.post("/redistribute")
    assert "within 1.6% of the best possible cost" in page_text(client.get("/redistribute"))


def test_employee_has_no_run_button_or_nav_link(employee, api):
    text = page_text(employee.get("/redistribute"))
    assert "Only an owner can run the optimizer." in text
    assert "Run Optimizer" not in text
    assert "/redistribute" not in employee.get("/items").get_data(as_text=True)
