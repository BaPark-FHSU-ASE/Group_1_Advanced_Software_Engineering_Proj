"""The Dashboard (Layer 1: Custody) and its business buttons."""

from flask import Blueprint, flash, redirect, render_template, url_for

import api_client
from helpers import current_user_id, form_text, login_required, remember_roles

bp = Blueprint("dashboard", __name__)


@bp.route("/dashboard")
@login_required
def dashboard():
    businesses = api_client.get_dashboard(current_user_id())
    # Roles can change while someone is logged in (an owner promotes them),
    # so refresh the session's copy on every Dashboard visit.
    remember_roles(businesses)
    return render_template("dashboard.html", businesses=businesses)


@bp.route("/businesses", methods=["POST"])
@login_required
def add_business():
    business = api_client.add_business(current_user_id(), form_text("name"))
    remember_roles([{"role": "owner"}])  # they own the one they just made
    flash(f'Added business "{business["name"]}".', "success")
    return redirect(url_for("dashboard.dashboard"))


@bp.route("/businesses/<int:business_id>/rename", methods=["POST"])
@login_required
def rename_business(business_id):
    business = api_client.rename_business(current_user_id(), business_id, form_text("name"))
    flash(f'Renamed business to "{business["name"]}".', "success")
    return redirect(url_for("dashboard.dashboard"))


@bp.route("/businesses/<int:business_id>/retire", methods=["POST"])
@login_required
def retire_business(business_id):
    business = api_client.retire_business(current_user_id(), business_id)
    flash(f'Retired "{business["name"]}".', "success")
    return redirect(url_for("dashboard.dashboard"))


@bp.route("/businesses/<int:business_id>/buildings", methods=["POST"])
@login_required
def add_building(business_id):
    building = api_client.add_building(
        current_user_id(), business_id,
        form_text("street_address"), form_text("city"), form_text("state"),
    )
    # A new building is empty, so land on it with the Add Room form open.
    flash(f'Added building at {building["street_address"]}, {building["city"]}. '
          "Add a room next.", "success")
    return redirect(url_for("buildings.building", building_id=building["building_id"], add="room"))
