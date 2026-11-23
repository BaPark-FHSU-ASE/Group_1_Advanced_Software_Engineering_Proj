"""Item types (REQ-9): what kinds of things are tracked, what a new one
costs, and how long one lasts (REQ-23). Anyone can look; owners edit."""

from flask import Blueprint, flash, redirect, render_template, url_for

import api_client
from helpers import current_user_id, form_float, form_int, form_text, login_required

bp = Blueprint("item_types", __name__)


def _fields():
    """The form's fields. Blank cost or service life means "not set" (None)."""
    return dict(
        name=form_text("name"),
        description=form_text("description") or None,
        replacement_cost=form_float("replacement_cost"),
        service_life_days=form_int("service_life_days"),
    )


@bp.route("/item-types")
@login_required
def item_types():
    return render_template("item_types.html",
                           item_types=api_client.get_item_types(current_user_id()))


@bp.route("/item-types", methods=["POST"])
@login_required
def add_item_type():
    item_type = api_client.add_item_type(current_user_id(), **_fields())
    flash(f'Added item type "{item_type["name"]}".', "success")
    return redirect(url_for("item_types.item_types"))


@bp.route("/item-types/<int:item_type_id>/edit", methods=["POST"])
@login_required
def edit_item_type(item_type_id):
    item_type = api_client.update_item_type(current_user_id(), item_type_id, **_fields())
    flash(f'Saved "{item_type["name"]}".', "success")
    return redirect(url_for("item_types.item_types"))


@bp.route("/item-types/<int:item_type_id>/delete", methods=["POST"])
@login_required
def delete_item_type(item_type_id):
    api_client.delete_item_type(current_user_id(), item_type_id)
    flash("Deleted the item type.", "success")
    return redirect(url_for("item_types.item_types"))
