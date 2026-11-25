import math

from flask import Blueprint, jsonify
from app.Validation_Helper import ValidationError, parse_body, require_query_int
from app.access import AccessError, require_record_role
from app.retire_helper import require_not_retired
from app.repositories import building_route_repository

building_route_bp = Blueprint("building_route_bp", __name__)

COST_FIELDS = {"distance_miles": float, "fixed_dispatch_cost": float, "cost_per_unit_mile": float}

def _check_number(data, key, label, problems, *, minimum, more_than=False):
    """A finite number from the body, or None after adding a plain sentence to problems."""
    value = data.get(key)
    if value is None:
        problems.append(f"{label} is required.")
        return None
    if not math.isfinite(value):
        problems.append(f"{label} must be a number.")
        return None
    if more_than and value <= minimum:
        problems.append(f"{label} must be more than {minimum:g}.")
        return None
    if not more_than and value < minimum:
        problems.append(f"{label} must be {minimum:g} or more.")
        return None
    return value


def _costs(data):
    problems = []
    distance = _check_number(data, "distance_miles", "Distance in miles", problems, minimum=0)
    dispatch = _check_number(data, "fixed_dispatch_cost", "Dispatch cost", problems, minimum=0, more_than=True)
    rate = _check_number(data, "cost_per_unit_mile", "Cost per unit mile", problems, minimum=0)
    if problems:
        raise ValidationError(" ".join(problems))
    return distance, dispatch, rate


def _require_owner_of_both_ends(user_id, from_building_id, to_building_id):
    require_record_role("building", from_building_id, user_id, "owner")
    require_record_role("building", to_building_id, user_id, "owner")


def _visible_route_or_404(user_id, route_id):
    route = building_route_repository.get_visible_by_id(user_id, route_id)
    if route is None:
        raise AccessError("Route not found", 404)
    return route


def _answer(user_id, route):
    labels = building_route_repository.building_labels(user_id)
    return route.to_dict(labels.get(route.from_building_id), labels.get(route.to_building_id))


@building_route_bp.route("/routes", methods=["GET"])
def get_routes():
    user_id = require_query_int("user_id")
    labels = building_route_repository.building_labels(user_id)
    routes = building_route_repository.get_visible(user_id)
    return jsonify([
        route.to_dict(labels.get(route.from_building_id), labels.get(route.to_building_id))
        for route in routes
    ])


@building_route_bp.route("/routes", methods=["POST"])
def create_route():
    data = parse_body(
        required={"user_id": int, "from_building_id": int, "to_building_id": int},
        optional=COST_FIELDS,
    )
    user_id = data["user_id"]
    from_id, to_id = data["from_building_id"], data["to_building_id"]
    distance, dispatch, rate = _costs(data)
    if from_id == to_id:
        raise ValidationError("Choose two different buildings.")

    _require_owner_of_both_ends(user_id, from_id, to_id)
    require_not_retired("building", from_id)
    require_not_retired("building", to_id)
    if building_route_repository.get_by_pair(from_id, to_id) is not None:
        labels = building_route_repository.building_labels(user_id)
        raise ValidationError(
            f"There is already a route from {labels.get(from_id)} to {labels.get(to_id)}.", 409
        )

    route = building_route_repository.create(from_id, to_id, distance, dispatch, rate)
    return jsonify(_answer(user_id, route)), 201


@building_route_bp.route("/routes/<int:route_id>", methods=["PUT"])
def update_route(route_id):
    data = parse_body(required={"user_id": int}, optional=COST_FIELDS)
    user_id = data["user_id"]
    distance, dispatch, rate = _costs(data)

    route = _visible_route_or_404(user_id, route_id)
    _require_owner_of_both_ends(user_id, route.from_building_id, route.to_building_id)
    route = building_route_repository.update(route_id, distance, dispatch, rate)
    return jsonify(_answer(user_id, route))


@building_route_bp.route("/routes/<int:route_id>", methods=["DELETE"])
def delete_route(route_id):
    user_id = require_query_int("user_id")
    route = _visible_route_or_404(user_id, route_id)
    _require_owner_of_both_ends(user_id, route.from_building_id, route.to_building_id)
    building_route_repository.delete(route_id)
    return "", 204