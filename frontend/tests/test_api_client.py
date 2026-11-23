"""Tests for api_client.py that don't need the real API running.

Each wrapper is checked for the method, path and body it sends (the shapes
in API_CONTRACT.md). A tiny local HTTP server checks the plumbing: JSON
in and out, error sentences, query strings and CSV.
"""

import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

import api_client

U = 7  # the logged-in user's id in every call below


def _unused_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def test_unreachable_api_raises_api_unavailable(monkeypatch):
    monkeypatch.setattr(api_client, "API_URL", f"http://127.0.0.1:{_unused_port()}")
    with pytest.raises(api_client.ApiUnavailable):
        api_client.set_target(1, 1, 1, 5)


def test_default_url_is_port_5001():
    # Unless STOCKDADDY_API_URL is set, the frontend looks for the API on 5001.
    import os
    if "STOCKDADDY_API_URL" not in os.environ:
        assert api_client.API_URL == "http://127.0.0.1:5001"


# --- What each wrapper sends --------------------------------------------------

@pytest.fixture
def sent(monkeypatch):
    """Record every request instead of sending it."""
    calls = []
    replies = {}

    def fake_send(method, path, body=None, query=None, timeout=None):
        calls.append((method, path, body, query))
        reply = replies.get(path, {})
        return 200, json.dumps(reply).encode(), "application/json"

    monkeypatch.setattr(api_client, "_send", fake_send)
    return calls, replies


CASES = [
    (lambda: api_client.register("A", "B", "a@b.c", "pw123456"),
     ("POST", "/auth/register",
      {"first_name": "A", "last_name": "B", "email": "a@b.c", "password": "pw123456"}, None)),
    (lambda: api_client.login("a@b.c", "pw"),
     ("POST", "/auth/login", {"email": "a@b.c", "password": "pw"}, None)),
    (lambda: api_client.get_dashboard(U), ("GET", "/reports/dashboard", None, {"user_id": U})),
    (lambda: api_client.get_building_report(U, 3),
     ("GET", "/reports/buildings/3", None, {"user_id": U})),
    (lambda: api_client.get_storage_report(U, 4),
     ("GET", "/reports/storages/4", None, {"user_id": U})),
    (lambda: api_client.get_item_detail(U, 9), ("GET", "/reports/items/9", None, {"user_id": U})),
    (lambda: api_client.get_compliance(U), ("GET", "/reports/compliance", None, {"user_id": U})),
    (lambda: api_client.get_expired_items(U),
     ("GET", "/reports/expired_items", None, {"user_id": U})),
    (lambda: api_client.add_business(U, "Acme"),
     ("POST", "/businesses", {"owner_id": U, "name": "Acme"}, None)),
    (lambda: api_client.rename_business(U, 2, "New"),
     ("PUT", "/businesses/2", {"user_id": U, "name": "New"}, None)),
    (lambda: api_client.retire_business(U, 2),
     ("POST", "/businesses/2/retire", {"user_id": U}, None)),
    (lambda: api_client.add_building(U, 2, "1 Main", "Hays", "Kansas"),
     ("POST", "/buildings", {"user_id": U, "business_id": 2, "street_address": "1 Main",
                             "city": "Hays", "state": "Kansas"}, None)),
    (lambda: api_client.update_building(U, 5, 2, "1 Main", "Hays", "Kansas"),
     ("PUT", "/buildings/5", {"user_id": U, "business_id": 2, "street_address": "1 Main",
                              "city": "Hays", "state": "Kansas"}, None)),
    (lambda: api_client.retire_building(U, 5), ("POST", "/buildings/5/retire", {"user_id": U}, None)),
    (lambda: api_client.add_room(U, 5, "Shop"),
     ("POST", "/rooms", {"user_id": U, "building_id": 5, "location": "Shop"}, None)),
    (lambda: api_client.update_room(U, 6, 5, "Shop"),
     ("PUT", "/rooms/6", {"user_id": U, "building_id": 5, "location": "Shop"}, None)),
    (lambda: api_client.retire_room(U, 6), ("POST", "/rooms/6/retire", {"user_id": U}, None)),
    (lambda: api_client.add_storage(U, 6, "Locker"),
     ("POST", "/storages", {"user_id": U, "room_id": 6, "storage_type": "Locker"}, None)),
    (lambda: api_client.update_storage(U, 8, 6, "Shelf"),
     ("PUT", "/storages/8", {"user_id": U, "room_id": 6, "storage_type": "Shelf"}, None)),
    (lambda: api_client.retire_storage(U, 8), ("POST", "/storages/8/retire", {"user_id": U}, None)),
    (lambda: api_client.update_item(U, 9, 1, 8, "In Use", "Gun A"),
     ("PUT", "/items/9", {"user_id": U, "item_type_id": 1, "storage_id": 8,
                          "item_status": "In Use", "item_name": "Gun A"}, None)),
    (lambda: api_client.retire_item(U, 9), ("POST", "/items/9/retire", {"user_id": U}, None)),
    (lambda: api_client.add_item_type(U, "Saw", "Circular", 120.0, 365),
     ("POST", "/item_types", {"user_id": U, "name": "Saw", "description": "Circular",
                              "replacement_cost": 120.0, "service_life_days": 365}, None)),
    (lambda: api_client.add_item_type(U, "Saw"),
     ("POST", "/item_types", {"user_id": U, "name": "Saw"}, None)),
    (lambda: api_client.update_item_type(U, 3, "Saw", None, 99.5, None),
     ("PUT", "/item_types/3", {"user_id": U, "name": "Saw", "replacement_cost": 99.5}, None)),
    (lambda: api_client.delete_item_type(U, 3), ("DELETE", "/item_types/3", None, {"user_id": U})),
    (lambda: api_client.get_members(U, 2), ("GET", "/businesses/2/members", None, {"user_id": U})),
    (lambda: api_client.add_member(U, 2, "crew@x.y", "employee"),
     ("POST", "/businesses/2/members", {"user_id": U, "email": "crew@x.y", "role": "employee"}, None)),
    (lambda: api_client.change_member_role(U, 2, 4, "owner"),
     ("PUT", "/businesses/2/members/4", {"user_id": U, "role": "owner"}, None)),
    (lambda: api_client.remove_member(U, 2, 4),
     ("DELETE", "/businesses/2/members/4", None, {"user_id": U})),
    (lambda: api_client.get_routes(U), ("GET", "/routes", None, {"user_id": U})),
    (lambda: api_client.add_route(U, 1, 2, 30.0, 50.0, 0.25),
     ("POST", "/routes", {"user_id": U, "from_building_id": 1, "to_building_id": 2,
                          "distance_miles": 30.0, "fixed_dispatch_cost": 50.0,
                          "cost_per_unit_mile": 0.25}, None)),
    (lambda: api_client.update_route(U, 3, 31.0, 55.0, 0.3),
     ("PUT", "/routes/3", {"user_id": U, "distance_miles": 31.0, "fixed_dispatch_cost": 55.0,
                           "cost_per_unit_mile": 0.3}, None)),
    (lambda: api_client.delete_route(U, 3), ("DELETE", "/routes/3", None, {"user_id": U})),
    (lambda: api_client.search_movements(U, item_type_id=1, q="gun"),
     ("GET", "/movements", None, {"user_id": U, "item_type_id": 1, "q": "gun"})),
    (lambda: api_client.run_plan(U), ("POST", "/plans", {"user_id": U}, None)),
]


@pytest.mark.parametrize("call, expected", CASES, ids=[c[1][0] + " " + c[1][1] for c in CASES])
def test_wrapper_sends_contract_shape(sent, call, expected):
    calls, _ = sent
    call()
    assert calls == [expected]


def test_add_items_returns_new_ids(sent):
    calls, replies = sent
    replies["/items/bulk"] = {"item_ids": [10, 11]}
    assert api_client.add_items(U, 8, 1, 2, "Gun") == [10, 11]
    assert calls == [("POST", "/items/bulk", {"user_id": U, "storage_id": 8, "item_type_id": 1,
                                              "quantity": 2, "item_name": "Gun"}, None)]


def test_add_items_leaves_out_a_blank_name(sent):
    calls, replies = sent
    replies["/items/bulk"] = {"item_ids": [10]}
    api_client.add_items(U, 8, 1, 1, "")
    assert "item_name" not in calls[0][2]


def test_change_item_status_sends_destination_only_when_given(sent):
    calls, replies = sent
    replies["/items/9/status"] = {"changed": True}
    assert api_client.change_item_status(U, 9, "In Transit") is True
    assert api_client.change_item_status(U, 9, "In Storage", 8) is True
    assert calls[0][2] == {"user_id": U, "status": "In Transit"}
    assert calls[1][2] == {"user_id": U, "status": "In Storage", "storage_id": 8}


def test_set_target_sends_owner_and_user_id(sent):
    calls, _ = sent
    api_client.set_target(U, 1, 2, 5)
    assert calls == [("PUT", "/target_quantities/1/2",
                      {"owner_id": U, "user_id": U, "target_qty": 5}, None)]


def test_item_types_come_back_sorted_by_name(sent):
    _, replies = sent
    replies["/item_types"] = [{"name": "saw"}, {"name": "Drill"}, {"name": "ladder"}]
    assert [t["name"] for t in api_client.get_item_types(U)] == ["Drill", "ladder", "saw"]


def test_unknown_movement_filter_is_refused(sent):
    with pytest.raises(ValueError):
        api_client.search_movements(U, colour="red")


# --- Plumbing against a real (tiny) HTTP server --------------------------------

class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path.startswith("/movements/export"):
            self._reply(200, "date,item\n2026-11-01,Gun #1\n", "text/csv")
        elif self.path.startswith("/echo"):
            self._reply(200, json.dumps({"path": self.path}))
        else:
            self._reply(404, json.dumps({"error": "Building not found"}))

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.path == "/rooms/1/retire":
            self._reply(409, json.dumps({"error": "Can't retire this room: 2 items still inside"}))
        else:
            self._reply(201, json.dumps({"got": body}))

    def _reply(self, status, text, ctype="application/json"):
        data = text.encode()
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


@pytest.fixture
def server(monkeypatch):
    httpd = HTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setattr(api_client, "API_URL", f"http://127.0.0.1:{httpd.server_port}")
    yield
    httpd.shutdown()


def test_error_sentence_comes_through(server):
    with pytest.raises(api_client.ApiError) as e:
        api_client.retire_room(1, 1)
    assert e.value.status == 409
    assert e.value.message == "Can't retire this room: 2 items still inside"


def test_404_is_an_api_error(server):
    with pytest.raises(api_client.ApiError) as e:
        api_client.get_building_report(1, 999)
    assert e.value.status == 404


def test_query_string_skips_empty_filters(server):
    status, reply = api_client._request("GET", "/echo", query={"user_id": 1, "q": "", "x": None})
    assert reply["path"] == "/echo?user_id=1"


def test_body_is_sent_as_json(server):
    assert api_client.add_room(1, 2, "Shop") == {
        "got": {"user_id": 1, "building_id": 2, "location": "Shop"}}


def test_csv_export_returns_text(server):
    assert api_client.export_movements_csv(1).startswith("date,item\n")
