from flask import Blueprint, jsonify, request
from app.repositories import item_repository

item_bp = Blueprint("item_bp", __name__)


@item_bp.route("/items", methods=["GET"])
def get_items():
    items = item_repository.get_all()
    return jsonify([item.to_dict() for item in items])


@item_bp.route("/items", methods=["POST"])
def create_item():
    data = request.get_json()
    item = item_repository.create(
        item_type_id=data["item_type_id"],
        storage_id=data.get("storage_id"),
        item_name=data.get("item_name"),
        item_status=data.get("item_status", "In Storage"),
    )
    return jsonify(item.to_dict()), 201


@item_bp.route("/items/<int:item_id>", methods=["GET"])
def get_item(item_id):
    item = item_repository.get_by_id(item_id)
    if item is None:
        return jsonify({"error": "Item not found"}), 404
    return jsonify(item.to_dict())


@item_bp.route("/items/<int:item_id>", methods=["PUT"])
def update_item(item_id):
    data = request.get_json()
    item = item_repository.update(
        item_id=item_id,
        item_type_id=data["item_type_id"],
        storage_id=data.get("storage_id"),
        item_name=data.get("item_name"),
        item_status=data["item_status"],
    )
    if item is None:
        return jsonify({"error": "Item not found"}), 404
    return jsonify(item.to_dict())


@item_bp.route("/items/<int:item_id>", methods=["DELETE"])
def delete_item(item_id):
    deleted = item_repository.delete(item_id)
    if not deleted:
        return jsonify({"error": "Item not found"}), 404
    return "", 204