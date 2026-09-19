from flask import Blueprint, jsonify, request
from app.repositories import owner_repository

owner_bp = Blueprint("owner_bp", __name__)


@owner_bp.route("/owners", methods=["GET"])
def get_owners():
    owners = owner_repository.get_all()
    return jsonify([owner.to_dict() for owner in owners])


@owner_bp.route("/owners", methods=["POST"])
def create_owner():
    data = request.get_json()
    owner = owner_repository.create(
        first_name=data["first_name"],
        last_name=data["last_name"],
        email=data["email"],
        password_hash=data["password_hash"],
    )
    return jsonify(owner.to_dict()), 201


@owner_bp.route("/owners/<int:owner_id>", methods=["GET"])
def get_owner(owner_id):
    owner = owner_repository.get_by_id(owner_id)
    if owner is None:
        return jsonify({"error": "Owner not found"}), 404
    return jsonify(owner.to_dict())


@owner_bp.route("/owners/<int:owner_id>", methods=["PUT"])
def update_owner(owner_id):
    data = request.get_json()
    owner = owner_repository.update(
        owner_id=owner_id,
        first_name=data["first_name"],
        last_name=data["last_name"],
        email=data["email"],
    )
    if owner is None:
        return jsonify({"error": "Owner not found"}), 404
    return jsonify(owner.to_dict())


@owner_bp.route("/owners/<int:owner_id>", methods=["DELETE"])
def delete_owner(owner_id):
    deleted = owner_repository.delete(owner_id)
    if not deleted:
        return jsonify({"error": "Owner not found"}), 404
    return "", 204