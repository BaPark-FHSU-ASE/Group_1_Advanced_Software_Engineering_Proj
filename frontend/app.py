from flask import Flask, render_template, redirect, url_for, request, session

import db

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

    businesses = db.get_dashboard_hierarchy()
    return render_template("dashboard.html", user=session["user"], businesses=businesses)


# ---------------------------------------------------------------------------
# Buildings
# ---------------------------------------------------------------------------

@app.route("/building/<int:building_id>")
def building(building_id):
    if "user" not in session:
        return redirect(url_for("login"))
    building_data = db.get_building(building_id)
    if building_data is None:
        return redirect(url_for("dashboard"))
    return render_template("building.html", user=session["user"], building=building_data)


# ---------------------------------------------------------------------------
# Items — Layer 1: Custody
# ---------------------------------------------------------------------------

@app.route("/items")
def items():
    if "user" not in session:
        return redirect(url_for("login"))
    item_list = db.get_items()
    return render_template("items.html", user=session["user"], items=item_list)


@app.route("/items/<int:item_id>")
def item_detail(item_id):
    if "user" not in session:
        return redirect(url_for("login"))
    item = db.get_item_detail(item_id)
    if item is None:
        return redirect(url_for("items"))
    return render_template("item_detail.html", user=session["user"], item=item)


# ---------------------------------------------------------------------------
# Compliance — Layer 2
# ---------------------------------------------------------------------------

@app.route("/compliance")
def compliance():
    if "user" not in session:
        return redirect(url_for("login"))
    report = db.get_compliance_report()
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
