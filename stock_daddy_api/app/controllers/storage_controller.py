from flask import Blueprint, jsonify
from app.Validation_Helper import parse_body
from app.repositories import storage_repository

storage_bp = Blueprint("storage_bp", __name__)


@storage_bp.route("/storages", methods=["GET"])
def get_storages():
    storage_units = storage_repository.get_all()
    return jsonify([storage_unit.to_dict() for storage_unit in storage_units])


@storage_bp.route("/storages", methods=["POST"])
def create_storage():
    data = parse_body(
        required={"room_id": int, "storage_type": str},
    )
    storage_unit = storage_repository.create(
        room_id=data["room_id"],
        storage_type=data["storage_type"],
    )
    return jsonify(storage_unit.to_dict()), 201


@storage_bp.route("/storages/<int:storage_id>", methods=["GET"])
def get_storage(storage_id):
    storage_unit = storage_repository.get_by_id(storage_id)
    if storage_unit is None:
        return jsonify({"error": "Storage not found"}), 404
    return jsonify(storage_unit.to_dict())


@storage_bp.route("/storages/<int:storage_id>", methods=["PUT"])
def update_storage(storage_id):
    data = parse_body(
        required={"room_id": int, "storage_type": str},
    )
    storage_unit = storage_repository.update(
        storage_id=storage_id,
        room_id=data["room_id"],
        storage_type=data["storage_type"],
    )
    if storage_unit is None:
        return jsonify({"error": "Storage not found"}), 404
    return jsonify(storage_unit.to_dict())


@storage_bp.route("/storages/<int:storage_id>", methods=["DELETE"])
def delete_storage(storage_id):
    deleted = storage_repository.delete(storage_id)
    if not deleted:
        return jsonify({"error": "Storage not found"}), 404
    return "", 204