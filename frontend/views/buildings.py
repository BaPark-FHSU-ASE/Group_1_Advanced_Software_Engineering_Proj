"""A building's page, plus adding rooms, storage units and stock targets."""

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

import api_client
import db
from helpers import current_user_id, login_required

bp = Blueprint("buildings", __name__)


@bp.route("/building/<int:building_id>")
@login_required
def building(building_id):
    building_data = db.get_building(current_user_id(), building_id)
    if building_data is None:
        return redirect(url_for("dashboard.dashboard"))
    return render_template(
        "building.html",
        user=session["user"],
        building=building_data,
        item_types=db.get_item_types(),
    )


@bp.route("/building/<int:building_id>/targets", methods=["POST"])
@login_required
def set_target(building_id):
    """Set or change one stock target for this building (REQ-15).

    Saves through the Stock Daddy API (stock_daddy_api/), not db.py.
    Saving a target that already exists updates it instead of adding a
    second one.
    """
    owner_id = current_user_id()
    if db.get_building(owner_id, building_id) is None:
        return redirect(url_for("dashboard.dashboard"))

    item_type_id = request.form.get("item_type_id", type=int)
    target_qty = request.form.get("target_qty", type=int)
    names = {t["id"]: t["name"] for t in db.get_item_types()}
    if item_type_id not in names or target_qty is None or target_qty < 0:
        flash("Pick an item type and enter a target of 0 or more.", "error")
        return redirect(url_for("buildings.building", building_id=building_id))

    try:
        _, created = api_client.set_target(owner_id, building_id, item_type_id, target_qty)
    except api_client.ApiUnavailable:
        flash("Couldn't reach the Stock Daddy API, so the target wasn't saved. "
              "Restart the app and try again.", "error")
    except api_client.ApiError as e:
        flash(f"The target wasn't saved: {e.message}", "error")
    else:
        verb = "Set" if created else "Updated"
        flash(f"{verb} the {names[item_type_id]} target to {target_qty}.", "success")
    return redirect(url_for("buildings.building", building_id=building_id))


@bp.route("/building/<int:building_id>/rooms", methods=["POST"])
@login_required
def add_room(building_id):
    name = request.form.get("name", "").strip()
    if not name:
        flash("Room name is required.", "error")
    else:
        try:
            db.add_room(current_user_id(), building_id, name)
            flash(f'Added room "{name}".', "success")
        except db.NotFoundOrNotOwned:
            return redirect(url_for("dashboard.dashboard"))
    return redirect(url_for("buildings.building", building_id=building_id))


@bp.route("/rooms/<int:room_id>/storage", methods=["POST"])
@login_required
def add_storage(room_id):
    storage_type = request.form.get("storage_type", "").strip()
    building_id = request.form.get("building_id", type=int)
    if not storage_type:
        flash("Storage type is required.", "error")
        if building_id:
            return redirect(url_for("buildings.building", building_id=building_id))
        return redirect(url_for("dashboard.dashboard"))
    try:
        _, building_id = db.add_storage(current_user_id(), room_id, storage_type)
    except db.NotFoundOrNotOwned:
        return redirect(url_for("dashboard.dashboard"))
    flash(f'Added storage unit "{storage_type}".', "success")
    return redirect(url_for("buildings.building", building_id=building_id))
