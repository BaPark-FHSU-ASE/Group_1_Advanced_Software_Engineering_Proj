from flask import Blueprint, jsonify
from app.Validation_Helper import parse_body, query_flag, require_query_int
from app.access import require_record_role
from app.retire_helper import require_not_retired, retire_record
from app.repositories import storage_repository

storage_bp = Blueprint("storage_bp", __name__)



@storage_bp.route("/storages", methods=["GET"])
def get_storages():
    user_id = require_query_int("user_id")
    storage_units = storage_repository.get_all(
        include_retired=query_flag("include_retired"), user_id=user_id
    )
    return jsonify([storage_unit.to_dict() for storage_unit in storage_units])


@storage_bp.route("/storages", methods=["POST"])
def create_storage():
    data = parse_body(
        required={"user_id": int, "room_id": int, "storage_type": str},
    )
    require_record_role("room", data["room_id"], data["user_id"], "owner")
    require_not_retired("room", data["room_id"])
    storage_unit = storage_repository.create(
        room_id=data["room_id"],
        storage_type=data["storage_type"],
    )
    return jsonify(storage_unit.to_dict()), 201


@storage_bp.route("/storages/<int:storage_id>", methods=["GET"])
def get_storage(storage_id):
    require_record_role("storage", storage_id, require_query_int("user_id"))
    storage_unit = storage_repository.get_by_id(storage_id)
    return jsonify(storage_unit.to_dict())


@storage_bp.route("/storages/<int:storage_id>", methods=["PUT"])
def update_storage(storage_id):
    data = parse_body(
        required={"user_id": int, "room_id": int, "storage_type": str},
    )
    # Owner of the storage unit's business now, and of the room it is moving to.
    require_record_role("storage", storage_id, data["user_id"], "owner")
    require_record_role("room", data["room_id"], data["user_id"], "owner")
    require_not_retired("room", data["room_id"])
    storage_unit = storage_repository.update(
        storage_id=storage_id,
        room_id=data["room_id"],
        storage_type=data["storage_type"],
    )
    return jsonify(storage_unit.to_dict())


@storage_bp.route("/storages/<int:storage_id>", methods=["DELETE"])
def delete_storage(storage_id):
    require_record_role("storage", storage_id, require_query_int("user_id"), "owner")
    storage_repository.delete(storage_id)
    return "", 204

@storage_bp.route("/storages/<int:storage_id>/retire", methods=["POST"])
def retire_storage(storage_id):
    return retire_record("storage", storage_id, storage_repository)