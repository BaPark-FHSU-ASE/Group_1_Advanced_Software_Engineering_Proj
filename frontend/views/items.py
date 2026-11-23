"""The item list, adding items, and an item's own page (Layer 1: Custody)."""

from flask import Blueprint, Response, flash, redirect, render_template, request, url_for

import api_client
from helpers import current_user_id, form_int, form_text, login_required

bp = Blueprint("items", __name__)


@bp.route("/items")
@login_required
def items():
    item_list = api_client.get_items(current_user_id())
    expired_count = sum(1 for item in item_list if item.get("expired"))
    return render_template("items.html", items=item_list, expired_count=expired_count)


@bp.route("/items/new", methods=["GET", "POST"])
@login_required
def new_items():
    """Add one item, or several of one type at once (REQ-6, REQ-14)."""
    user_id = current_user_id()
    error = None
    form = {
        "storage_id": request.values.get("storage_id", type=int),
        "item_type_id": form_int("item_type_id"),
        "quantity": request.form.get("quantity", 1, type=int),
        "name": form_text("name"),
    }

    if request.method == "POST":
        try:
            new_ids = api_client.add_items(user_id, form["storage_id"], form["item_type_id"],
                                           form["quantity"], form["name"])
        except api_client.ApiError as e:
            # Stay on the form so nothing typed is lost. 404 means the
            # storage unit or type isn't one of theirs.
            error = ("That storage unit or item type wasn't found."
                     if e.status == 404 else e.message)
        else:
            flash(f"Added {len(new_ids)} item{'s' if len(new_ids) != 1 else ''}.", "success")
            if len(new_ids) == 1:
                return redirect(url_for("items.item_detail", item_id=new_ids[0]))
            return redirect(url_for("items.items"))

    return render_template(
        "item_form.html",
        item_types=api_client.get_item_types(user_id),
        storages=api_client.get_storage_choices(user_id),
        form=form,
        max_qty=api_client.MAX_ITEMS_PER_ADD,
        error=error,
    )


@bp.route("/items/<int:item_id>")
@login_required
def item_detail(item_id):
    user_id = current_user_id()
    item = api_client.get_item_detail(user_id, item_id)
    is_item_owner = item.get("role") == "owner"
    # An In Transit item needs somewhere to arrive, so offer the user's
    # storage units alongside the status buttons.
    storages = api_client.get_storage_choices(user_id) if item["status"] == "In Transit" else []
    return render_template(
        "item_detail.html",
        item=item,
        statuses=api_client.ITEM_STATUSES,
        storages=storages,
        is_item_owner=is_item_owner,
        item_types=api_client.get_item_types(user_id) if is_item_owner else [],
    )


@bp.route("/items/<int:item_id>/status", methods=["POST"])
@login_required
def item_status(item_id):
    """Change status (REQ-11). The API writes the item and its movement
    record in one transaction (REQ-12), so history can't be skipped."""
    new_status = request.form.get("status", "")
    changed = api_client.change_item_status(current_user_id(), item_id, new_status,
                                            form_int("storage_id"))
    if changed:
        flash(f"Marked as {new_status}.", "success")
    return redirect(url_for("items.item_detail", item_id=item_id))


@bp.route("/items/<int:item_id>/edit", methods=["POST"])
@login_required
def edit_item(item_id):
    """Rename or retype an item (owner only). Where it is and its status are
    sent back unchanged; those only change through /status, which logs them."""
    user_id = current_user_id()
    current = api_client.get_item_detail(user_id, item_id)
    api_client.update_item(user_id, item_id, form_int("item_type_id"),
                           current["storage_id"], current["status"], form_text("name"))
    flash("Saved the item.", "success")
    return redirect(url_for("items.item_detail", item_id=item_id))


@bp.route("/items/<int:item_id>/retire", methods=["POST"])
@login_required
def retire_item(item_id):
    api_client.retire_item(current_user_id(), item_id)
    flash("Retired the item. Its history is kept.", "success")
    return redirect(url_for("items.items"))


# --- Movement history search and export (REQ-13) ----------------------------

def _movement_filters():
    """The search form's filters from the query string, leaving out blanks."""
    filters = {}
    for name in ("item_id", "item_type_id", "building_id"):
        value = request.args.get(name, type=int)
        if value is not None:
            filters[name] = value
    for name in ("status", "date_from", "date_to", "q"):
        value = request.args.get(name, "").strip()
        if value:
            filters[name] = value
    return filters


@bp.route("/movements")
@login_required
def movements():
    user_id = current_user_id()
    filters = _movement_filters()
    buildings = [b for biz in api_client.get_dashboard(user_id) for b in biz["buildings"]]
    return render_template(
        "movements.html",
        rows=api_client.search_movements(user_id, **filters),
        filters=filters,
        item_types=api_client.get_item_types(user_id),
        buildings=buildings,
        statuses=api_client.ITEM_STATUSES,
    )


@bp.route("/movements/export.csv")
@login_required
def export_movements():
    """The same rows as the search, as a CSV download."""
    csv_text = api_client.export_movements_csv(current_user_id(), **_movement_filters())
    return Response(
        csv_text,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=movement_history.csv"},
    )
