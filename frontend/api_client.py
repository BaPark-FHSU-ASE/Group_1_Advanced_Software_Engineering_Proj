"""Every call from the frontend to the Stock Daddy API (stock_daddy_api/).

The frontend never opens the database itself; each page reads and writes
through the functions below. API_CONTRACT.md (next to this file) documents
each endpoint and the shape it returns.

Every function takes the logged-in user's id first and passes it to the
API as user_id, which is how the API decides what that user may see and do.

Errors:
- ApiUnavailable: the API couldn't be reached at all.
- ApiError: the API said no. .status is the HTTP status and .message is the
  API's own sentence, written to be shown to the user as-is.

Uses only the standard library (urllib), so the frontend needs no extra
packages to talk to the API.
"""

import json
import os
import urllib.error
import urllib.parse
import urllib.request

API_URL = os.environ.get("STOCKDADDY_API_URL", "http://127.0.0.1:5001").rstrip("/")
TIMEOUT_SECONDS = 5
# The optimizer can take up to its own deadline, so plans get longer.
PLAN_TIMEOUT_SECONDS = 40

MAX_ITEMS_PER_ADD = 100
ITEM_STATUSES = ("In Storage", "In Use", "In Transit")


class ApiUnavailable(Exception):
    """The API couldn't be reached (not running, wrong port, ...)."""


class ApiError(Exception):
    """The API answered with an error (4xx/5xx)."""

    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


def _url(path, query=None):
    if query:
        query = {k: v for k, v in query.items() if v not in (None, "")}
    return API_URL + path + ("?" + urllib.parse.urlencode(query) if query else "")


def _send(method, path, body=None, query=None, timeout=TIMEOUT_SECONDS):
    """Make the request. Returns (status, raw bytes, content type)."""
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        _url(path, query),
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status, response.read(), response.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        try:
            message = json.loads(e.read()).get("error", e.reason)
        except (ValueError, AttributeError):
            message = e.reason
        raise ApiError(e.code, message) from None
    except (urllib.error.URLError, OSError) as e:
        raise ApiUnavailable(str(e)) from None


def _request(method, path, body=None, query=None, timeout=TIMEOUT_SECONDS):
    """Make a JSON request. Returns (status, parsed JSON or None)."""
    status, raw, _ = _send(method, path, body, query, timeout)
    return status, (json.loads(raw) if raw else None)


def _get(path, user_id, **query):
    return _request("GET", path, query={"user_id": user_id, **query})[1]


def _post(path, user_id, **body):
    return _request("POST", path, {"user_id": user_id, **body})[1]


def _put(path, user_id, **body):
    return _request("PUT", path, {"user_id": user_id, **body})[1]


def _delete(path, user_id):
    _request("DELETE", path, query={"user_id": user_id})


# --- Accounts ---------------------------------------------------------------

def register(first_name, last_name, email, password):
    """Create an account. Returns the new owner (see API_CONTRACT.md)."""
    return _request("POST", "/auth/register", {
        "first_name": first_name, "last_name": last_name,
        "email": email, "password": password,
    })[1]


def login(email, password):
    """Check a login. Returns the owner, or raises ApiError (401) if wrong."""
    return _request("POST", "/auth/login", {"email": email, "password": password})[1]


# --- Reports (read-only pages) ---------------------------------------------

def get_dashboard(user_id):
    return _get("/reports/dashboard", user_id)


def get_building_report(user_id, building_id):
    return _get(f"/reports/buildings/{building_id}", user_id)


def get_storage_report(user_id, storage_id):
    return _get(f"/reports/storages/{storage_id}", user_id)


def get_items(user_id):
    return _get("/reports/items", user_id)


def get_item_detail(user_id, item_id):
    return _get(f"/reports/items/{item_id}", user_id)


def get_compliance(user_id):
    return _get("/reports/compliance", user_id)


def get_expired_items(user_id):
    return _get("/reports/expired_items", user_id)


def get_storage_choices(user_id):
    return _get("/reports/storage_choices", user_id)


# --- Businesses --------------------------------------------------------------

def add_business(user_id, name):
    # POST /businesses names the new business's owner with owner_id.
    return _request("POST", "/businesses", {"owner_id": user_id, "name": name})[1]


def rename_business(user_id, business_id, name):
    return _put(f"/businesses/{business_id}", user_id, name=name)


def retire_business(user_id, business_id):
    return _post(f"/businesses/{business_id}/retire", user_id)


# --- Buildings ---------------------------------------------------------------

def add_building(user_id, business_id, street_address, city, state):
    return _post("/buildings", user_id, business_id=business_id,
                 street_address=street_address, city=city, state=state)


def update_building(user_id, building_id, business_id, street_address, city, state):
    return _put(f"/buildings/{building_id}", user_id, business_id=business_id,
                street_address=street_address, city=city, state=state)


def retire_building(user_id, building_id):
    return _post(f"/buildings/{building_id}/retire", user_id)


# --- Rooms -------------------------------------------------------------------

def add_room(user_id, building_id, name):
    return _post("/rooms", user_id, building_id=building_id, location=name)


def update_room(user_id, room_id, building_id, name):
    return _put(f"/rooms/{room_id}", user_id, building_id=building_id, location=name)


def retire_room(user_id, room_id):
    return _post(f"/rooms/{room_id}/retire", user_id)


# --- Storage units -----------------------------------------------------------

def add_storage(user_id, room_id, storage_type):
    return _post("/storages", user_id, room_id=room_id, storage_type=storage_type)


def update_storage(user_id, storage_id, room_id, storage_type):
    return _put(f"/storages/{storage_id}", user_id, room_id=room_id,
                storage_type=storage_type)


def retire_storage(user_id, storage_id):
    return _post(f"/storages/{storage_id}/retire", user_id)


# --- Items -------------------------------------------------------------------

def add_items(user_id, storage_id, item_type_id, quantity, name=""):
    """Add `quantity` items of one type in one action (REQ-14).
    Returns the new item ids."""
    body = {"storage_id": storage_id, "item_type_id": item_type_id, "quantity": quantity}
    if name:
        body["item_name"] = name
    return _post("/items/bulk", user_id, **body)["item_ids"]


def change_item_status(user_id, item_id, status, storage_id=None):
    """Change an item's status; the API logs the movement (REQ-11, REQ-12).
    Returns True if it changed, False if it already had that status."""
    body = {"status": status}
    if storage_id:
        body["storage_id"] = storage_id
    return _post(f"/items/{item_id}/status", user_id, **body)["changed"]


def update_item(user_id, item_id, item_type_id, storage_id, item_status, name):
    return _put(f"/items/{item_id}", user_id, item_type_id=item_type_id,
                storage_id=storage_id, item_status=item_status, item_name=name)


def retire_item(user_id, item_id):
    return _post(f"/items/{item_id}/retire", user_id)


# --- Item types (REQ-9) ------------------------------------------------------

def get_item_types(user_id):
    """Item types as the API returns them, sorted by name."""
    return sorted(_get("/item_types", user_id), key=lambda t: t["name"].lower())


def _item_type_body(name, description, replacement_cost, service_life_days):
    body = {"name": name}
    if description:
        body["description"] = description
    if replacement_cost is not None:
        body["replacement_cost"] = replacement_cost
    if service_life_days is not None:
        body["service_life_days"] = service_life_days
    return body


def add_item_type(user_id, name, description=None, replacement_cost=None,
                  service_life_days=None):
    return _post("/item_types", user_id, **_item_type_body(
        name, description, replacement_cost, service_life_days))


def update_item_type(user_id, item_type_id, name, description=None,
                     replacement_cost=None, service_life_days=None):
    return _put(f"/item_types/{item_type_id}", user_id, **_item_type_body(
        name, description, replacement_cost, service_life_days))


def delete_item_type(user_id, item_type_id):
    _delete(f"/item_types/{item_type_id}", user_id)


# --- Stock targets (REQ-15) --------------------------------------------------

def set_target(owner_id, building_id, item_type_id, target_qty):
    """Create or update a building's target for one item type (REQ-15).

    Returns (target, created): the saved target as a dict, and True if it
    was new or False if an existing target was updated.
    """
    status, target = _request(
        "PUT",
        f"/target_quantities/{building_id}/{item_type_id}",
        {"owner_id": owner_id, "user_id": owner_id, "target_qty": target_qty},
    )
    return target, status == 201


# --- Team --------------------------------------------------------------------

def get_members(user_id, business_id):
    return _get(f"/businesses/{business_id}/members", user_id)


def add_member(user_id, business_id, email, role):
    return _post(f"/businesses/{business_id}/members", user_id, email=email, role=role)


def change_member_role(user_id, business_id, member_id, role):
    return _put(f"/businesses/{business_id}/members/{member_id}", user_id, role=role)


def remove_member(user_id, business_id, member_id):
    _delete(f"/businesses/{business_id}/members/{member_id}", user_id)


# --- Route costs (REQ-17) ----------------------------------------------------

def get_routes(user_id):
    return _get("/routes", user_id)


def add_route(user_id, from_building_id, to_building_id, distance_miles,
              fixed_dispatch_cost, cost_per_unit_mile):
    return _post("/routes", user_id, from_building_id=from_building_id,
                 to_building_id=to_building_id, distance_miles=distance_miles,
                 fixed_dispatch_cost=fixed_dispatch_cost,
                 cost_per_unit_mile=cost_per_unit_mile)


def update_route(user_id, route_id, distance_miles, fixed_dispatch_cost, cost_per_unit_mile):
    return _put(f"/routes/{route_id}", user_id, distance_miles=distance_miles,
                fixed_dispatch_cost=fixed_dispatch_cost,
                cost_per_unit_mile=cost_per_unit_mile)


def delete_route(user_id, route_id):
    _delete(f"/routes/{route_id}", user_id)


# --- Movement history (REQ-13) -----------------------------------------------

MOVEMENT_FILTERS = ("item_id", "item_type_id", "building_id", "status",
                    "date_from", "date_to", "q")


def search_movements(user_id, **filters):
    """Movement rows matching the filters (any of MOVEMENT_FILTERS)."""
    return _get("/movements", user_id, **_movement_filters(filters))


def export_movements_csv(user_id, **filters):
    """The same rows as search_movements, as CSV text."""
    _, raw, _ = _send("GET", "/movements/export",
                      query={"user_id": user_id, **_movement_filters(filters)})
    return raw.decode("utf-8")


def _movement_filters(filters):
    unknown = set(filters) - set(MOVEMENT_FILTERS)
    if unknown:
        raise ValueError(f"Unknown movement filter(s): {', '.join(sorted(unknown))}")
    return filters


# --- Redistribution plan (REQ-18 to REQ-21, REQ-24) --------------------------

def run_plan(user_id):
    """Run the optimizer on the user's inventory. Returns the plan dict.
    Raises ApiError (409) when no plan can cover every shortage."""
    return _request("POST", "/plans", {"user_id": user_id},
                    timeout=PLAN_TIMEOUT_SECONDS)[1]
