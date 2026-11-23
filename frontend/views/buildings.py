"""A building's page and everything on it: the building itself, its rooms,
storage units and stock targets, the floor view (UI-REQ-1) and a storage
unit's own page (UI-REQ-2)."""

from flask import Blueprint, flash, redirect, render_template, request, url_for

import api_client
from helpers import current_user_id, form_int, form_text, login_required

bp = Blueprint("buildings", __name__)


def _to_building(building_id, **args):
    return redirect(url_for("buildings.building", building_id=building_id, **args))


# --- The building -------------------------------------------------------------

@bp.route("/building/<int:building_id>")
@login_required
def building(building_id):
    user_id = current_user_id()
    report = api_client.get_building_report(user_id, building_id)
    # Floor view (UI-REQ-1) draws the same rooms as tiles instead of a list.
    view = "floor" if request.args.get("view") == "floor" else "list"
    return render_template(
        "building.html",
        building=report,
        is_building_owner=report["role"] == "owner",
        item_types=api_client.get_item_types(user_id) if report["role"] == "owner" else [],
        view=view,
    )


@bp.route("/building/<int:building_id>/edit", methods=["POST"])
@login_required
def edit_building(building_id):
    api_client.update_building(
        current_user_id(), building_id, form_int("business_id"),
        form_text("street_address"), form_text("city"), form_text("state"),
    )
    flash("Saved the building's address.", "success")
    return _to_building(building_id)


@bp.route("/building/<int:building_id>/retire", methods=["POST"])
@login_required
def retire_building(building_id):
    api_client.retire_building(current_user_id(), building_id)
    flash("Retired the building.", "success")
    return redirect(url_for("dashboard.dashboard"))


@bp.route("/building/<int:building_id>/targets", methods=["POST"])
@login_required
def set_target(building_id):
    """Set or change one stock target for this building (REQ-15). Saving a
    target that already exists updates it instead of adding a second one."""
    item_type_id = form_int("item_type_id")
    if item_type_id is None:
        # Without a type there's no URL to send, so this one stays here.
        flash("Pick an item type.", "error")
        return _to_building(building_id)

    user_id = current_user_id()
    target_qty = form_int("target_qty")
    _, created = api_client.set_target(user_id, building_id, item_type_id, target_qty)
    names = {t["item_type_id"]: t["name"] for t in api_client.get_item_types(user_id)}
    verb = "Set" if created else "Updated"
    flash(f"{verb} the {names.get(item_type_id, 'item')} target to {target_qty}.", "success")
    return _to_building(building_id)


# --- Rooms ----------------------------------------------------------------------

@bp.route("/building/<int:building_id>/rooms", methods=["POST"])
@login_required
def add_room(building_id):
    room = api_client.add_room(current_user_id(), building_id, form_text("name"))
    flash(f'Added room "{room["location"]}".', "success")
    return _to_building(building_id)


@bp.route("/rooms/<int:room_id>/edit", methods=["POST"])
@login_required
def edit_room(room_id):
    building_id = form_int("building_id")
    room = api_client.update_room(current_user_id(), room_id, building_id, form_text("name"))
    flash(f'Renamed the room to "{room["location"]}".', "success")
    return _to_building(building_id)


@bp.route("/rooms/<int:room_id>/retire", methods=["POST"])
@login_required
def retire_room(room_id):
    api_client.retire_room(current_user_id(), room_id)
    flash("Retired the room.", "success")
    return _to_building(form_int("building_id"))


# --- Storage units ----------------------------------------------------------------

@bp.route("/rooms/<int:room_id>/storage", methods=["POST"])
@login_required
def add_storage(room_id):
    storage = api_client.add_storage(current_user_id(), room_id, form_text("storage_type"))
    flash(f'Added storage unit "{storage["storage_type"]}".', "success")
    return _to_building(form_int("building_id"))


@bp.route("/storage/<int:storage_id>")
@login_required
def storage(storage_id):
    """One storage unit and everything in it (UI-REQ-2)."""
    report = api_client.get_storage_report(current_user_id(), storage_id)
    return render_template("storage.html", storage=report)


@bp.route("/storage/<int:storage_id>/edit", methods=["POST"])
@login_required
def edit_storage(storage_id):
    api_client.update_storage(current_user_id(), storage_id, form_int("room_id"),
                              form_text("storage_type"))
    flash("Saved the storage unit.", "success")
    return redirect(url_for("buildings.storage", storage_id=storage_id))


@bp.route("/storage/<int:storage_id>/retire", methods=["POST"])
@login_required
def retire_storage(storage_id):
    api_client.retire_storage(current_user_id(), storage_id)
    flash("Retired the storage unit.", "success")
    return _to_building(form_int("building_id"))
