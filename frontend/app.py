from flask import Flask, render_template, redirect, url_for, request, session, flash

import db
import redistribution

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
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        owner = db.verify_owner(email, password)
        if owner is not None:
            session["user"] = owner["first_name"]
            session["owner_id"] = owner["owner_id"]
            return redirect(url_for("dashboard"))
        error = "Invalid email or password."
    return render_template("login.html", error=error)


@app.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not first_name or not last_name or not email or not password:
            error = "All fields are required."
        elif password != confirm:
            error = "Passwords do not match."
        elif len(password) < 8:
            error = "Password must be at least 8 characters."
        else:
            try:
                owner_id = db.register_owner(first_name, last_name, email, password)
                session["user"] = first_name
                session["owner_id"] = owner_id
                return redirect(url_for("dashboard"))
            except db.EmailAlreadyRegistered:
                error = "An account with that email already exists."

    return render_template("register.html", error=error)


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

    businesses = db.get_dashboard_hierarchy(session["owner_id"])
    return render_template("dashboard.html", user=session["user"], businesses=businesses)


@app.route("/businesses", methods=["POST"])
def add_business():
    if "user" not in session:
        return redirect(url_for("login"))
    name = request.form.get("name", "").strip()
    if not name:
        flash("Business name is required.", "error")
    else:
        db.add_business(session["owner_id"], name)
        flash(f'Added business "{name}".', "success")
    return redirect(url_for("dashboard"))


@app.route("/businesses/<int:business_id>/rename", methods=["POST"])
def rename_business(business_id):
    if "user" not in session:
        return redirect(url_for("login"))
    name = request.form.get("name", "").strip()
    if not name:
        flash("Business name is required.", "error")
        return redirect(url_for("dashboard"))
    try:
        db.rename_business(session["owner_id"], business_id, name)
    except db.NotFoundOrNotOwned:
        return redirect(url_for("dashboard"))
    flash(f'Renamed business to "{name}".', "success")
    return redirect(url_for("dashboard"))


@app.route("/businesses/<int:business_id>/buildings", methods=["POST"])
def add_building(business_id):
    if "user" not in session:
        return redirect(url_for("login"))
    street = request.form.get("street_address", "").strip()
    city = request.form.get("city", "").strip()
    state = request.form.get("state", "").strip()
    if not street or not city or not state:
        flash("Street address, city and state are all required.", "error")
        return redirect(url_for("dashboard"))
    try:
        building_id = db.add_building(session["owner_id"], business_id, street, city, state)
    except db.NotFoundOrNotOwned:
        return redirect(url_for("dashboard"))
    # A new building is empty, so land on it with the Add Room form open.
    flash(f"Added building at {street}, {city}. Add a room next.", "success")
    return redirect(url_for("building", building_id=building_id, add="room"))


# ---------------------------------------------------------------------------
# Buildings
# ---------------------------------------------------------------------------

@app.route("/building/<int:building_id>")
def building(building_id):
    if "user" not in session:
        return redirect(url_for("login"))
    building_data = db.get_building(session["owner_id"], building_id)
    if building_data is None:
        return redirect(url_for("dashboard"))
    return render_template("building.html", user=session["user"], building=building_data)


@app.route("/building/<int:building_id>/rooms", methods=["POST"])
def add_room(building_id):
    if "user" not in session:
        return redirect(url_for("login"))
    name = request.form.get("name", "").strip()
    if not name:
        flash("Room name is required.", "error")
    else:
        try:
            db.add_room(session["owner_id"], building_id, name)
            flash(f'Added room "{name}".', "success")
        except db.NotFoundOrNotOwned:
            return redirect(url_for("dashboard"))
    return redirect(url_for("building", building_id=building_id))


@app.route("/rooms/<int:room_id>/storage", methods=["POST"])
def add_storage(room_id):
    if "user" not in session:
        return redirect(url_for("login"))
    storage_type = request.form.get("storage_type", "").strip()
    building_id = request.form.get("building_id", type=int)
    if not storage_type:
        flash("Storage type is required.", "error")
        if building_id:
            return redirect(url_for("building", building_id=building_id))
        return redirect(url_for("dashboard"))
    try:
        _, building_id = db.add_storage(session["owner_id"], room_id, storage_type)
    except db.NotFoundOrNotOwned:
        return redirect(url_for("dashboard"))
    flash(f'Added storage unit "{storage_type}".', "success")
    return redirect(url_for("building", building_id=building_id))


# ---------------------------------------------------------------------------
# Items — Layer 1: Custody
# ---------------------------------------------------------------------------

@app.route("/items")
def items():
    if "user" not in session:
        return redirect(url_for("login"))
    item_list = db.get_items(session["owner_id"])
    return render_template("items.html", user=session["user"], items=item_list)


@app.route("/items/new", methods=["GET", "POST"])
def new_items():
    if "user" not in session:
        return redirect(url_for("login"))
    owner_id = session["owner_id"]
    error = None
    form = {
        "storage_id": request.values.get("storage_id", type=int),
        "item_type_id": request.form.get("item_type_id", type=int),
        "quantity": request.form.get("quantity", 1, type=int),
        "name": request.form.get("name", "").strip(),
    }

    if request.method == "POST":
        if not form["storage_id"] or not form["item_type_id"]:
            error = "Choose an item type and a storage unit."
        elif form["quantity"] is None or not (1 <= form["quantity"] <= db.MAX_ITEMS_PER_ADD):
            error = f"Quantity must be between 1 and {db.MAX_ITEMS_PER_ADD}."
        else:
            try:
                new_ids = db.add_items(owner_id, form["storage_id"], form["item_type_id"],
                                       form["quantity"], form["name"])
            except db.NotFoundOrNotOwned:
                error = "That storage unit or item type wasn't found."
            else:
                flash(f"Added {len(new_ids)} item{'s' if len(new_ids) != 1 else ''}.", "success")
                if len(new_ids) == 1:
                    return redirect(url_for("item_detail", item_id=new_ids[0]))
                return redirect(url_for("items"))

    return render_template(
        "item_form.html",
        user=session["user"],
        item_types=db.get_item_types(),
        storages=db.get_storage_choices(owner_id),
        form=form,
        max_qty=db.MAX_ITEMS_PER_ADD,
        error=error,
    )


@app.route("/items/<int:item_id>")
def item_detail(item_id):
    if "user" not in session:
        return redirect(url_for("login"))
    owner_id = session["owner_id"]
    item = db.get_item_detail(owner_id, item_id)
    if item is None:
        return redirect(url_for("items"))
    # An In Transit item needs somewhere to arrive, so offer the owner's
    # storage units alongside the status buttons.
    storages = db.get_storage_choices(owner_id) if item["status"] == "In Transit" else []
    return render_template("item_detail.html", user=session["user"], item=item,
                           statuses=db.ITEM_STATUSES, storages=storages)


@app.route("/items/<int:item_id>/status", methods=["POST"])
def item_status(item_id):
    if "user" not in session:
        return redirect(url_for("login"))
    new_status = request.form.get("status", "")
    storage_id = request.form.get("storage_id", type=int)
    try:
        changed = db.update_item_status(session["owner_id"], item_id, new_status, storage_id)
    except db.NotFoundOrNotOwned:
        return redirect(url_for("items"))
    except ValueError as e:
        flash(str(e), "error")
    else:
        if changed:
            flash(f"Marked as {new_status}.", "success")
    return redirect(url_for("item_detail", item_id=item_id))


# ---------------------------------------------------------------------------
# Compliance — Layer 2
# ---------------------------------------------------------------------------

@app.route("/compliance")
def compliance():
    if "user" not in session:
        return redirect(url_for("login"))
    report = db.get_compliance_report(session["owner_id"])
    return render_template("compliance.html", user=session["user"], report=report)


# ---------------------------------------------------------------------------
# Redistribute — Layer 3: Decision Support
# ---------------------------------------------------------------------------

@app.route("/redistribute", methods=["GET", "POST"])
def redistribute():
    """GET shows the empty page; POST (the Run Optimizer button) runs Scott's
    engine on the owner's current inventory and shows the plan."""
    if "user" not in session:
        return redirect(url_for("login"))

    plan = {"generated": False}
    if request.method == "POST":
        try:
            plan = redistribution.generate_plan(session["owner_id"])
        except redistribution.NoFeasiblePlan:
            flash(
                "No plan could cover every shortage: some item can't be moved "
                "from another site and has no replacement cost set.",
                "error",
            )
    return render_template("redistribute.html", user=session["user"], plan=plan)


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)
