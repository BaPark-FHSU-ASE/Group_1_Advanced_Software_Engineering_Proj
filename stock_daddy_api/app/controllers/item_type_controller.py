from flask import Blueprint, jsonify, request
from app.repositories import item_type_repository

item_type_bp = Blueprint("item_type_bp", __name__)


@item_type_bp.route("/item_types", methods=["GET"])
def get_item_types():
    item_types = item_type_repository.get_all()
    return jsonify([item_type.to_dict() for item_type in item_types])


@item_type_bp.route("/item_types", methods=["POST"])
def create_item_type():
    data = request.get_json()
    item_type = item_type_repository.create(
        name=data["name"],
        description=data.get("description"),
        replacement_cost=data.get("replacement_cost"),
    )
    return jsonify(item_type.to_dict()), 201


@item_type_bp.route("/item_types/<int:item_type_id>", methods=["GET"])
def get_item_type(item_type_id):
    item_type = item_type_repository.get_by_id(item_type_id)
    if item_type is None:
        return jsonify({"error": "Item type not found"}), 404
    return jsonify(item_type.to_dict())


@item_type_bp.route("/item_types/<int:item_type_id>", methods=["PUT"])
def update_item_type(item_type_id):
    data = request.get_json()
    item_type = item_type_repository.update(
        item_type_id=item_type_id,
        name=data["name"],
        description=data.get("description"),
        replacement_cost=data.get("replacement_cost"),
    )
    if item_type is None:
        return jsonify({"error": "Item type not found"}), 404
    return jsonify(item_type.to_dict())


@item_type_bp.route("/item_types/<int:item_type_id>", methods=["DELETE"])
def delete_item_type(item_type_id):
    deleted = item_type_repository.delete(item_type_id)
    if not deleted:
        return jsonify({"error": "Item type not found"}), 404
    return "", 204