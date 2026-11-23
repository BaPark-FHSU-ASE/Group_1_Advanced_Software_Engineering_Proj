"""How every page reacts when an API call fails (helpers.register_api_error_handlers)."""

from flask import Blueprint

import api_client
from app import app

# A throwaway page that raises whatever the test asks for.
_probe = Blueprint("probe", __name__)
_raise = {}


@_probe.route("/_probe")
def probe():
    raise _raise["error"]


if "probe" not in app.blueprints:
    app.register_blueprint(_probe)


def _get(client, error, **kw):
    _raise["error"] = error
    return client.get("/_probe", **kw)


def test_unreachable_api_shows_a_friendly_page(client):
    resp = _get(client, api_client.ApiUnavailable("refused"))
    assert resp.status_code == 503
    assert "Couldn't reach the Stock Daddy API" in resp.get_data(as_text=True)


def test_not_found_goes_to_dashboard_without_saying_why(client):
    resp = _get(client, api_client.ApiError(404, "Building not found"))
    assert resp.status_code == 302 and resp.location.endswith("/dashboard")
    with client.session_transaction() as sess:
        assert "_flashes" not in sess


def test_other_errors_flash_the_apis_sentence_and_go_back(client):
    resp = _get(client, api_client.ApiError(409, "Can't retire this room: 2 items still inside"),
                headers={"Referer": "http://localhost/building/1"})
    assert resp.location == "http://localhost/building/1"
    with client.session_transaction() as sess:
        assert sess["_flashes"] == [("error", "Can't retire this room: 2 items still inside")]


def test_referer_from_another_site_is_ignored(client):
    resp = _get(client, api_client.ApiError(400, "bad"),
                headers={"Referer": "https://evil.example/phish"})
    assert resp.location.endswith("/dashboard")
