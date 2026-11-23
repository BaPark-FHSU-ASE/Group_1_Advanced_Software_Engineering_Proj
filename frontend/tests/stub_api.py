"""A stand-in for the Stock Daddy API, for clicking through the frontend
before the real endpoints in API_CONTRACT.md exist.

It answers every endpoint the pages call with the sample data in
tests/sample_data.py. Nothing is saved: buttons that add, edit or retire
things say they worked, but the page won't change.

Run it from frontend/, in its own terminal, before starting the frontend:

    python -m tests.stub_api

It listens on port 5001, where the frontend looks for the API, so the
frontend uses it instead of starting the real one. Stop it with Ctrl+C.

Log in with any email and password. An email starting with "crew" logs
in as Jess, an employee, so you can see what employees see.
"""

from flask import Flask, Response, jsonify, request

from tests import sample_data as S

app = Flask(__name__)
EMPLOYEE_ID = S.EMPLOYEE["owner_id"]


def _user_id():
    raw = request.args.get("user_id")
    if raw is None:
        raw = (request.get_json(silent=True) or {}).get("user_id")
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _role():
    return "employee" if _user_id() == EMPLOYEE_ID else "owner"


def _owner_only():
    if _role() != "owner":
        return jsonify({"error": "The owner role is required"}), 403
    return None


# --- Auth ----------------------------------------------------------------------

@app.post("/auth/login")
def login():
    email = (request.get_json(silent=True) or {}).get("email", "")
    return jsonify(S.EMPLOYEE if email.lower().startswith("crew") else S.OWNER)


@app.post("/auth/register")
def register():
    body = request.get_json(silent=True) or {}
    if len(body.get("password", "")) < 8:
        return jsonify({"error": "Password must be at least 8 characters."}), 400
    return jsonify({**S.OWNER, "first_name": body.get("first_name") or "New",
                    "memberships": []}), 201


# --- Reports ---------------------------------------------------------------------

@app.get("/reports/dashboard")
def dashboard():
    return jsonify(S.dashboard(role=_role()))


@app.get("/reports/buildings/<int:building_id>")
def building(building_id):
    if building_id != 1:
        return jsonify({"error": "Building not found"}), 404
    return jsonify(S.building_report(role=_role()))


@app.get("/reports/storages/<int:storage_id>")
def storage(storage_id):
    return jsonify(S.storage_report(role=_role()))


@app.get("/reports/items")
def items():
    return jsonify(S.ITEMS)


@app.get("/reports/items/<int:item_id>")
def item(item_id):
    if item_id == 2:
        return jsonify(S.item_detail(item_id=2, status="In Transit", role=_role()))
    return jsonify(S.item_detail(item_id=item_id, role=_role(), expired=item_id == 1))


@app.get("/reports/compliance")
def compliance():
    return jsonify(S.COMPLIANCE)


@app.get("/reports/expired_items")
def expired():
    return jsonify(S.EXPIRED)


@app.get("/reports/storage_choices")
def storage_choices():
    return jsonify(S.STORAGE_CHOICES)


# --- Writes: pretend they worked ---------------------------------------------------

@app.post("/businesses")
def add_business():
    body = request.get_json(silent=True) or {}
    return jsonify({"business_id": 9, "name": body.get("name", ""), "owner_id": 1,
                    "retired": None}), 201


@app.put("/businesses/<int:business_id>")
def rename_business(business_id):
    if (denied := _owner_only()):
        return denied
    body = request.get_json(silent=True) or {}
    return jsonify({"business_id": business_id, "name": body.get("name", ""), "retired": None})


@app.post("/<kind>/<int:record_id>/retire")
def retire(kind, record_id):
    if (denied := _owner_only()):
        return denied
    if kind == "businesses":
        return jsonify({"business_id": record_id, "name": "Prairie Roofing"})
    # Show what the real API says when something's still inside.
    if kind in ("buildings", "rooms") and record_id == 1:
        return jsonify({"error": f"Can't retire this {kind[:-1]}: 2 storage units and "
                                 "3 items still inside"}), 409
    return jsonify({"retired": "2026-11-23 12:00:00"})


@app.post("/buildings")
def add_building():
    if (denied := _owner_only()):
        return denied
    body = request.get_json(silent=True) or {}
    return jsonify({**S.default_returns()["add_building"], **body, "building_id": 1}), 201


@app.put("/buildings/<int:building_id>")
def update_building(building_id):
    return _owner_only() or jsonify({"building_id": building_id})


@app.post("/rooms")
def add_room():
    body = request.get_json(silent=True) or {}
    return _owner_only() or (jsonify({"room_id": 4, "location": body.get("location", "")}), 201)


@app.put("/rooms/<int:room_id>")
def update_room(room_id):
    body = request.get_json(silent=True) or {}
    return _owner_only() or jsonify({"room_id": room_id, "location": body.get("location", "")})


@app.post("/storages")
def add_storage():
    body = request.get_json(silent=True) or {}
    return _owner_only() or (jsonify({"storage_id": 5,
                                      "storage_type": body.get("storage_type", "")}), 201)


@app.put("/storages/<int:storage_id>")
def update_storage(storage_id):
    return _owner_only() or jsonify({"storage_id": storage_id})


@app.post("/items/bulk")
def add_items():
    body = request.get_json(silent=True) or {}
    qty = body.get("quantity")
    if not isinstance(qty, int) or not 1 <= qty <= 100:
        return jsonify({"error": "quantity must be between 1 and 100"}), 400
    return jsonify({"item_ids": list(range(10, 10 + qty))}), 201


@app.post("/items/<int:item_id>/status")
def item_status(item_id):
    body = request.get_json(silent=True) or {}
    if item_id == 2 and not body.get("storage_id"):
        return jsonify({"error": "Choose where the item arrived."}), 400
    return jsonify({"changed": True})


@app.put("/items/<int:item_id>")
def update_item(item_id):
    return _owner_only() or jsonify({"item_id": item_id})


@app.get("/item_types")
def item_types():
    return jsonify(S.ITEM_TYPES)


@app.route("/item_types", methods=["POST"])
@app.route("/item_types/<int:item_type_id>", methods=["PUT"])
def save_item_type(item_type_id=9):
    body = request.get_json(silent=True) or {}
    return _owner_only() or jsonify({"item_type_id": item_type_id, "name": body.get("name", "")})


@app.delete("/item_types/<int:item_type_id>")
def delete_item_type(item_type_id):
    if (denied := _owner_only()):
        return denied
    return jsonify({"error": "That record refers to something that doesn't exist, "
                             "or other records still depend on it"}), 409


@app.put("/target_quantities/<int:building_id>/<int:item_type_id>")
def set_target(building_id, item_type_id):
    return jsonify({"target_qty": (request.get_json(silent=True) or {}).get("target_qty")})


# --- Team ------------------------------------------------------------------------

@app.get("/businesses/<int:business_id>/members")
def members(business_id):
    return jsonify(S.MEMBERS)


@app.post("/businesses/<int:business_id>/members")
def add_member(business_id):
    return _owner_only() or (jsonify(S.MEMBERS[1]), 201)


@app.put("/businesses/<int:business_id>/members/<int:member_id>")
def change_role(business_id, member_id):
    return _owner_only() or jsonify(S.MEMBERS[1])


@app.delete("/businesses/<int:business_id>/members/<int:member_id>")
def remove_member(business_id, member_id):
    if (denied := _owner_only()):
        return denied
    if member_id == 1:
        return jsonify({"error": "A business needs at least one owner"}), 409
    return "", 204


# --- Routes, movements, plans -------------------------------------------------------

@app.get("/routes")
def routes():
    return jsonify(S.ROUTES)


@app.route("/routes", methods=["POST"])
@app.route("/routes/<int:route_id>", methods=["PUT"])
def save_route(route_id=2):
    return _owner_only() or jsonify(S.ROUTES[0])


@app.delete("/routes/<int:route_id>")
def delete_route(route_id):
    return _owner_only() or ("", 204)


@app.get("/movements")
def movements():
    return jsonify(S.MOVEMENTS)


@app.get("/movements/export")
def export_movements():
    lines = ["date,item_name,item_type,from,to,status_change"]
    for m in S.MOVEMENTS:
        lines.append(",".join(str(m[k] or "") for k in
                              ("date", "item_name", "item_type", "from", "to", "status_change")))
    return Response("\n".join(lines) + "\n", mimetype="text/csv")


@app.post("/plans")
def plans():
    return _owner_only() or jsonify(S.PLAN)


if __name__ == "__main__":
    print(" * Stand-in API with sample data. Nothing you do is saved.")
    app.run(port=5001)
