"""The Dashboard (Layer 1: Custody) and its business buttons."""

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

import db
from helpers import current_user_id, login_required

bp = Blueprint("dashboard", __name__)


@bp.route("/dashboard")
@login_required
def dashboard():
    businesses = db.get_dashboard_hierarchy(current_user_id())
    return render_template("dashboard.html", user=session["user"], businesses=businesses)


@bp.route("/businesses", methods=["POST"])
@login_required
def add_business():
    name = request.form.get("name", "").strip()
    if not name:
        flash("Business name is required.", "error")
    else:
        db.add_business(current_user_id(), name)
        flash(f'Added business "{name}".', "success")
    return redirect(url_for("dashboard.dashboard"))


@bp.route("/businesses/<int:business_id>/rename", methods=["POST"])
@login_required
def rename_business(business_id):
    name = request.form.get("name", "").strip()
    if not name:
        flash("Business name is required.", "error")
        return redirect(url_for("dashboard.dashboard"))
    try:
        db.rename_business(current_user_id(), business_id, name)
    except db.NotFoundOrNotOwned:
        return redirect(url_for("dashboard.dashboard"))
    flash(f'Renamed business to "{name}".', "success")
    return redirect(url_for("dashboard.dashboard"))


@bp.route("/businesses/<int:business_id>/buildings", methods=["POST"])
@login_required
def add_building(business_id):
    street = request.form.get("street_address", "").strip()
    city = request.form.get("city", "").strip()
    state = request.form.get("state", "").strip()
    if not street or not city or not state:
        flash("Street address, city and state are all required.", "error")
        return redirect(url_for("dashboard.dashboard"))
    try:
        building_id = db.add_building(current_user_id(), business_id, street, city, state)
    except db.NotFoundOrNotOwned:
        return redirect(url_for("dashboard.dashboard"))
    # A new building is empty, so land on it with the Add Room form open.
    flash(f"Added building at {street}, {city}. Add a room next.", "success")
    return redirect(url_for("buildings.building", building_id=building_id, add="room"))
