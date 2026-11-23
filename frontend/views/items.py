"""The item list, adding items, and an item's own page (Layer 1: Custody)."""

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

import db
from helpers import current_user_id, login_required

bp = Blueprint("items", __name__)


@bp.route("/items")
@login_required
def items():
    item_list = db.get_items(current_user_id())
    return render_template("items.html", user=session["user"], items=item_list)


@bp.route("/items/new", methods=["GET", "POST"])
@login_required
def new_items():
    owner_id = current_user_id()
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
                    return redirect(url_for("items.item_detail", item_id=new_ids[0]))
                return redirect(url_for("items.items"))

    return render_template(
        "item_form.html",
        user=session["user"],
        item_types=db.get_item_types(),
        storages=db.get_storage_choices(owner_id),
        form=form,
        max_qty=db.MAX_ITEMS_PER_ADD,
        error=error,
    )


@bp.route("/items/<int:item_id>")
@login_required
def item_detail(item_id):
    owner_id = current_user_id()
    item = db.get_item_detail(owner_id, item_id)
    if item is None:
        return redirect(url_for("items.items"))
    # An In Transit item needs somewhere to arrive, so offer the owner's
    # storage units alongside the status buttons.
    storages = db.get_storage_choices(owner_id) if item["status"] == "In Transit" else []
    return render_template("item_detail.html", user=session["user"], item=item,
                           statuses=db.ITEM_STATUSES, storages=storages)


@bp.route("/items/<int:item_id>/status", methods=["POST"])
@login_required
def item_status(item_id):
    new_status = request.form.get("status", "")
    storage_id = request.form.get("storage_id", type=int)
    try:
        changed = db.update_item_status(current_user_id(), item_id, new_status, storage_id)
    except db.NotFoundOrNotOwned:
        return redirect(url_for("items.items"))
    except ValueError as e:
        flash(str(e), "error")
    else:
        if changed:
            flash(f"Marked as {new_status}.", "success")
    return redirect(url_for("items.item_detail", item_id=item_id))
