from flask import Blueprint, jsonify
from app.Validation_Helper import parse_body, require_query_int
from app.access import AccessError
from app.repositories import (
    business_lookup_repository,
    business_member_repository,
    item_type_repository,
)

item_type_bp = Blueprint("item_type_bp", __name__)


def _require_member(user_id):
    if not business_member_repository.has_role_anywhere(user_id):
        raise AccessError("Item type not found", 404)


def _require_owner(user_id):
    if not business_member_repository.has_role_anywhere(user_id, "owner"):
        raise AccessError("The owner role is required", 403)


def _require_can_change(user_id, item_type_id):
    _require_owner(user_id)
    if item_type_repository.get_by_id(item_type_id) is None:
        raise AccessError("Item type not found", 404)
    for business_id in business_lookup_repository.businesses_using_item_type(item_type_id):
        if business_member_repository.get_role(business_id, user_id) != "owner":
            raise AccessError(
                "Another business uses this item type, so it can't be changed", 403
            )


@item_type_bp.route("/item_types", methods=["GET"])
def get_item_types():
    user_id = require_query_int("user_id")
    if not business_member_repository.has_role_anywhere(user_id):
        return jsonify([])
    item_types = item_type_repository.get_all()
    return jsonify([item_type.to_dict() for item_type in item_types])


@item_type_bp.route("/item_types", methods=["POST"])
def create_item_type():
    data = parse_body(
        required={"user_id": int, "name": str},
        optional={"description": str, "replacement_cost": float},
    )
    _require_owner(data["user_id"])
    item_type = item_type_repository.create(
        name=data["name"],
        description=data.get("description"),
        replacement_cost=data.get("replacement_cost"),
    )
    return jsonify(item_type.to_dict()), 201


@item_type_bp.route("/item_types/<int:item_type_id>", methods=["GET"])
def get_item_type(item_type_id):
    _require_member(require_query_int("user_id"))
    item_type = item_type_repository.get_by_id(item_type_id)
    if item_type is None:
        return jsonify({"error": "Item type not found"}), 404
    return jsonify(item_type.to_dict())


@item_type_bp.route("/item_types/<int:item_type_id>", methods=["PUT"])
def update_item_type(item_type_id):
    data = parse_body(
        required={"user_id": int, "name": str},
        optional={"description": str, "replacement_cost": float},
    )
    _require_can_change(data["user_id"], item_type_id)
    item_type = item_type_repository.update(
        item_type_id=item_type_id,
        name=data["name"],
        description=data.get("description"),
        replacement_cost=data.get("replacement_cost"),
    )
    return jsonify(item_type.to_dict())


@item_type_bp.route("/item_types/<int:item_type_id>", methods=["DELETE"])
def delete_item_type(item_type_id):
    _require_can_change(require_query_int("user_id"), item_type_id)
    item_type_repository.delete(item_type_id)
    return "", 204