from flask import Blueprint, jsonify
from app.Validation_Helper import ValidationError, parse_body, query_flag, require_query_int
from app.access import AccessError, require_record_role
from app.retire_helper import require_not_retired, retire_record
from app.repositories import item_repository, item_type_repository

item_bp = Blueprint("item_bp", __name__)

MAX_ITEMS_PER_ADD = 100
MAX_ITEM_NAME_LENGTH = 100


def _names_for_new_items(item_type, quantity, typed_name):
    if typed_name:
        if quantity == 1:
            return [typed_name]
        return [f"{typed_name} #{number}" for number in range(1, quantity + 1)]
    already = item_repository.count_of_type(item_type.item_type_id)
    return [f"{item_type.name} #{already + number}" for number in range(1, quantity + 1)]


@item_bp.route("/items", methods=["GET"])
def get_items():
    user_id = require_query_int("user_id")
    items = item_repository.get_all(
        include_retired=query_flag("include_retired"), user_id=user_id
    )
    return jsonify([item.to_dict() for item in items])


@item_bp.route("/items", methods=["POST"])
def create_item():
    data = parse_body(
        required={"user_id": int, "item_type_id": int, "storage_id": int},
        optional={"item_name": str, "item_status": str},
    )
    require_record_role("storage", data["storage_id"], data["user_id"])
    require_not_retired("storage", data["storage_id"])
    item = item_repository.create(
        item_type_id=data["item_type_id"],
        storage_id=data["storage_id"],
        item_name=data.get("item_name"),
        item_status=data.get("item_status", "In Storage"),
    )
    return jsonify(item.to_dict()), 201

@item_bp.route("/items/bulk", methods=["POST"])
def create_items_in_bulk():
    data = parse_body(
        required={"user_id": int, "storage_id": int, "item_type_id": int, "quantity": int},
        optional={"item_name": str},
    )
    if not 1 <= data["quantity"] <= MAX_ITEMS_PER_ADD:
        raise ValidationError(f"Quantity must be between 1 and {MAX_ITEMS_PER_ADD}.")

    require_record_role("storage", data["storage_id"], data["user_id"])
    require_not_retired("storage", data["storage_id"])
    item_type = item_type_repository.get_by_id(data["item_type_id"])
    if item_type is None:
        raise AccessError("Item type not found", 404)

    names = _names_for_new_items(item_type, data["quantity"], data.get("item_name") or "")
    if any(len(name) > MAX_ITEM_NAME_LENGTH for name in names):
        raise ValidationError(f"Item name must be {MAX_ITEM_NAME_LENGTH} characters or fewer.")

    item_ids = item_repository.create_many(data["item_type_id"], data["storage_id"], names)
    return jsonify({"item_ids": item_ids}), 201

@item_bp.route("/items/<int:item_id>", methods=["GET"])
def get_item(item_id):
    require_record_role("item", item_id, require_query_int("user_id"))
    item = item_repository.get_by_id(item_id)
    return jsonify(item.to_dict())

@item_bp.route("/items/<int:item_id>", methods=["PUT"])
def update_item(item_id):
    data = parse_body(
        required={"user_id": int, "item_type_id": int, "storage_id": int, "item_status": str},
        optional={"item_name": str},
    )
    require_record_role("item", item_id, data["user_id"])
    current = item_repository.get_by_id(item_id)
    if data["item_type_id"] != current.item_type_id or data.get("item_name") != current.item_name:
        # Changing what the item is (its type or name) is the owner's job.
        require_record_role("item", item_id, data["user_id"], "owner")
    if data["storage_id"] != current.storage_id:
        # Moving it: the person needs access to the destination too.
        require_record_role("storage", data["storage_id"], data["user_id"])
        require_not_retired("storage", data["storage_id"])
    item = item_repository.update(
        item_id=item_id,
        item_type_id=data["item_type_id"],
        storage_id=data["storage_id"],
        item_name=data.get("item_name"),
        item_status=data["item_status"],
    )
    return jsonify(item.to_dict())


@item_bp.route("/items/<int:item_id>", methods=["DELETE"])
def delete_item(item_id):
    require_record_role("item", item_id, require_query_int("user_id"), "owner")
    item_repository.delete(item_id)
    return "", 204

@item_bp.route("/items/<int:item_id>/retire", methods=["POST"])
def retire_item(item_id):
    return retire_record("item", item_id, item_repository)