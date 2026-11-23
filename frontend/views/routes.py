"""Route costs between buildings (REQ-17): what it costs to send a truck
from one site to another. The optimizer plans with these."""

from flask import Blueprint, flash, redirect, render_template, url_for

import api_client
from helpers import current_user_id, form_float, form_int, login_required

bp = Blueprint("routes", __name__)


def _owned_buildings(user_id):
    """The buildings the user owns, for the From/To dropdowns."""
    return [
        {"id": b["id"], "name": b["name"], "business": biz["name"]}
        for biz in api_client.get_dashboard(user_id) if biz["role"] == "owner"
        for b in biz["buildings"]
    ]


@bp.route("/routes")
@login_required
def routes():
    user_id = current_user_id()
    return render_template(
        "routes.html",
        routes=api_client.get_routes(user_id),
        buildings=_owned_buildings(user_id),
    )


@bp.route("/routes", methods=["POST"])
@login_required
def add_route():
    route = api_client.add_route(
        current_user_id(), form_int("from_building_id"), form_int("to_building_id"),
        form_float("distance_miles"), form_float("fixed_dispatch_cost"),
        form_float("cost_per_unit_mile"),
    )
    flash(f'Added the route {route["from_label"]} → {route["to_label"]}.', "success")
    return redirect(url_for("routes.routes"))


@bp.route("/routes/<int:route_id>/edit", methods=["POST"])
@login_required
def edit_route(route_id):
    route = api_client.update_route(
        current_user_id(), route_id, form_float("distance_miles"),
        form_float("fixed_dispatch_cost"), form_float("cost_per_unit_mile"),
    )
    flash(f'Saved the route {route["from_label"]} → {route["to_label"]}.', "success")
    return redirect(url_for("routes.routes"))


@bp.route("/routes/<int:route_id>/delete", methods=["POST"])
@login_required
def delete_route(route_id):
    api_client.delete_route(current_user_id(), route_id)
    flash("Deleted the route.", "success")
    return redirect(url_for("routes.routes"))
