"""Login, register and logout through the API's /auth endpoints."""

import pytest

from tests.conftest import logged_in_client


@pytest.fixture
def anon():
    from app import app
    app.config["TESTING"] = True
    return app.test_client()


def test_login_page_renders(anon):
    assert "Log In" in anon.get("/login").get_data(as_text=True)


def test_login_sends_credentials_and_starts_session(anon, api):
    resp = anon.post("/login", data={"email": " dale@prairieroofing.example ",
                                     "password": "roofing123"})
    assert resp.status_code == 302 and resp.location.endswith("/dashboard")
    assert api.called("login") == [("dale@prairieroofing.example", "roofing123")]
    with anon.session_transaction() as sess:
        assert sess["owner_id"] == 1 and sess["user"] == "Dale" and sess["is_owner"] is True


def test_employee_login_is_not_an_owner(anon, api):
    from tests import sample_data
    api.returns["login"] = sample_data.EMPLOYEE
    anon.post("/login", data={"email": "crew@x", "password": "pw"})
    with anon.session_transaction() as sess:
        assert sess["is_owner"] is False


def test_wrong_password_shows_the_apis_message(anon, api):
    api.fail("login", 401, "Invalid email or password.")
    html = anon.post("/login", data={"email": "a@b.c", "password": "x"}).get_data(as_text=True)
    assert "Invalid email or password." in html
    with anon.session_transaction() as sess:
        assert "owner_id" not in sess


def test_register_sends_fields_and_logs_in(anon, api):
    resp = anon.post("/register", data={
        "first_name": "New", "last_name": "Person", "email": "new@x.y",
        "password": "longenough", "confirm_password": "longenough"})
    assert resp.status_code == 302
    assert api.called("register") == [("New", "Person", "new@x.y", "longenough")]
    with anon.session_transaction() as sess:
        assert sess["owner_id"] == 1


def test_register_mismatched_passwords_never_reach_the_api(anon, api):
    html = anon.post("/register", data={
        "first_name": "A", "last_name": "B", "email": "a@b.c",
        "password": "one11111", "confirm_password": "two22222"}).get_data(as_text=True)
    assert "Passwords do not match." in html
    assert api.called("register") == []


def test_register_shows_api_validation(anon, api):
    api.fail("register", 409, "An account with that email already exists.")
    html = anon.post("/register", data={
        "first_name": "A", "last_name": "B", "email": "a@b.c",
        "password": "pw", "confirm_password": "pw"}).get_data(as_text=True)
    assert "An account with that email already exists." in html


def test_logout_clears_session(api):
    client = logged_in_client()
    client.get("/logout")
    with client.session_transaction() as sess:
        assert "owner_id" not in sess


def test_pages_need_login(anon):
    for path in ["/dashboard", "/items", "/compliance", "/redistribute"]:
        resp = anon.get(path)
        assert resp.status_code == 302 and "/login" in resp.location
