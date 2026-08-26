from flask import Flask, render_template, redirect, url_for, request, session

app = Flask(__name__)
app.secret_key = "dev-secret-key"  # Change before production


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    if "user" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        # TODO: Replace with real DB auth (Ivan's layer)
        if username == "admin" and password == "admin":
            session["user"] = username
            return redirect(url_for("dashboard"))
        error = "Invalid username or password."
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Dashboard — Layer 1: Custody
# ---------------------------------------------------------------------------

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))

    # TODO: Replace with real DB query (Ivan's layer)
    businesses = [
        {
            "id": 1,
            "name": "Acme Roofing Co.",
            "buildings": [
                {
                    "id": 1,
                    "name": "Main Shop",
                    "address": "123 North Ave, Pittsburg, KS",
                    "rooms": [
                        {
                            "id": 1,
                            "name": "Tool Room",
                            "storages": [
                                {"id": 1, "name": "Shelf A", "type": "Shelf", "item_count": 12},
                                {"id": 2, "name": "Locker 1", "type": "Locker", "item_count": 5},
                            ]
                        },
                        {
                            "id": 2,
                            "name": "Equipment Bay",
                            "storages": [
                                {"id": 3, "name": "Rack 1", "type": "Shelf", "item_count": 8},
                            ]
                        },
                    ]
                },
                {
                    "id": 2,
                    "name": "South Storage",
                    "address": "456 South Rd, Pittsburg, KS",
                    "rooms": [
                        {
                            "id": 3,
                            "name": "Main Floor",
                            "storages": [
                                {"id": 4, "name": "Bin 1", "type": "Storage Unit", "item_count": 3},
                                {"id": 5, "name": "Toolbox A", "type": "Toolbox", "item_count": 7},
                            ]
                        },
                    ]
                },
            ]
        }
    ]
    return render_template("dashboard.html", user=session["user"], businesses=businesses)


# ---------------------------------------------------------------------------
# Buildings
# ---------------------------------------------------------------------------

@app.route("/building/<int:building_id>")
def building(building_id):
    if "user" not in session:
        return redirect(url_for("login"))
    # TODO: Query building by ID from DB
    building_data = {
        "id": building_id,
        "name": "Main Shop",
        "address": "123 North Ave, Pittsburg, KS",
        "rooms": [
            {
                "id": 1,
                "name": "Tool Room",
                "storages": [
                    {"id": 1, "name": "Shelf A", "type": "Shelf", "item_count": 12},
                    {"id": 2, "name": "Locker 1", "type": "Locker", "item_count": 5},
                ]
            },
            {
                "id": 2,
                "name": "Equipment Bay",
                "storages": [
                    {"id": 3, "name": "Rack 1", "type": "Shelf", "item_count": 8},
                ]
            },
        ],
        "compliance": [
            {"item_type": "Nail Gun",     "target": 5, "on_hand": 8, "available": 3, "variance": +3},
            {"item_type": "Harness",      "target": 6, "on_hand": 4, "available": 4, "variance": -2},
            {"item_type": "Compressor",   "target": 2, "on_hand": 2, "available": 1, "variance":  0},
            {"item_type": "Ladder",       "target": 4, "on_hand": 2, "available": 2, "variance": -2},
        ]
    }
    return render_template("building.html", user=session["user"], building=building_data)


# ---------------------------------------------------------------------------
# Items — Layer 1: Custody
# ---------------------------------------------------------------------------

@app.route("/items")
def items():
    if "user" not in session:
        return redirect(url_for("login"))
    # TODO: Query all items from DB
    item_list = [
        {"id": 1, "name": "Nail Gun #3",   "type": "Nail Gun",   "status": "In Storage", "building": "Main Shop",     "room": "Tool Room",    "storage": "Shelf A"},
        {"id": 2, "name": "Harness #1",    "type": "Harness",    "status": "In Use",     "building": "Main Shop",     "room": "Tool Room",    "storage": "Locker 1"},
        {"id": 3, "name": "Compressor #2", "type": "Compressor", "status": "In Transit", "building": "South Storage", "room": "Main Floor",   "storage": "Bin 1"},
        {"id": 4, "name": "Ladder #5",     "type": "Ladder",     "status": "In Storage", "building": "South Storage", "room": "Main Floor",   "storage": "Toolbox A"},
    ]
    return render_template("items.html", user=session["user"], items=item_list)


@app.route("/items/<int:item_id>")
def item_detail(item_id):
    if "user" not in session:
        return redirect(url_for("login"))
    # TODO: Query item + movement history from DB
    item = {
        "id": item_id,
        "name": "Nail Gun #3",
        "type": "Nail Gun",
        "status": "In Storage",
        "building": "Main Shop",
        "room": "Tool Room",
        "storage": "Shelf A",
        "date_added": "2024-03-01",
        "movement_history": [
            {"date": "2025-08-20", "from": "South Storage / Main Floor / Bin 1", "to": "Main Shop / Tool Room / Shelf A"},
            {"date": "2025-06-10", "from": "Main Shop / Tool Room / Shelf A",    "to": "South Storage / Main Floor / Bin 1"},
            {"date": "2025-01-15", "from": "—",                                  "to": "Main Shop / Tool Room / Shelf A"},
        ]
    }
    return render_template("item_detail.html", user=session["user"], item=item)


# ---------------------------------------------------------------------------
# Compliance — Layer 2
# ---------------------------------------------------------------------------

@app.route("/compliance")
def compliance():
    if "user" not in session:
        return redirect(url_for("login"))
    # TODO: Query surplus/shortage from DB
    report = [
        {"building": "Main Shop",     "item_type": "Nail Gun",   "target": 5, "on_hand": 8, "available": 3, "variance": +3},
        {"building": "Main Shop",     "item_type": "Harness",    "target": 6, "on_hand": 4, "available": 4, "variance": -2},
        {"building": "South Storage", "item_type": "Nail Gun",   "target": 4, "on_hand": 2, "available": 2, "variance": -2},
        {"building": "South Storage", "item_type": "Harness",    "target": 3, "on_hand": 5, "available": 5, "variance": +2},
        {"building": "Main Shop",     "item_type": "Compressor", "target": 2, "on_hand": 2, "available": 1, "variance":  0},
    ]
    return render_template("compliance.html", user=session["user"], report=report)


# ---------------------------------------------------------------------------
# Redistribute — Layer 3: Decision Support
# ---------------------------------------------------------------------------

@app.route("/redistribute")
def redistribute():
    if "user" not in session:
        return redirect(url_for("login"))
    # TODO: Call Scott's optimization engine
    plan = {
        "generated": False,
        "trips": [],
        "total_cost": 0.0,
        "greedy_cost": 0.0,
    }
    return render_template("redistribute.html", user=session["user"], plan=plan)


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)
