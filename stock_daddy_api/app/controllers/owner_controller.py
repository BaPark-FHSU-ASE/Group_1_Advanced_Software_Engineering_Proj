from flask import Blueprint, jsonify
from app.Validation_Helper import parse_body, require_query_int
from app.access import AccessError
from app.repositories import business_member_repository, owner_repository

owner_bp = Blueprint("owner_bp", __name__)


def _require_can_see(user_id, owner_id):
    if user_id != owner_id and not business_member_repository.share_a_business(user_id, owner_id):
        raise AccessError("Owner not found", 404)


def _require_self(user_id, owner_id):
    _require_can_see(user_id, owner_id)
    if user_id != owner_id:
        raise AccessError("You can only change your own account", 403)


@owner_bp.route("/owners", methods=["GET"])
def get_owners():
    owners = owner_repository.get_all(user_id=require_query_int("user_id"))
    return jsonify([owner.to_dict() for owner in owners])


@owner_bp.route("/owners", methods=["POST"])
def create_owner():
    data = parse_body(
        required={"first_name": str, "last_name": str, "email": str, "password_hash": str},
    )
    owner = owner_repository.create(
        first_name=data["first_name"],
        last_name=data["last_name"],
        email=data["email"],
        password_hash=data["password_hash"],
    )
    return jsonify(owner.to_dict()), 201


@owner_bp.route("/owners/<int:owner_id>", methods=["GET"])
def get_owner(owner_id):
    _require_can_see(require_query_int("user_id"), owner_id)
    owner = owner_repository.get_by_id(owner_id)
    if owner is None:
        return jsonify({"error": "Owner not found"}), 404
    return jsonify(owner.to_dict())


@owner_bp.route("/owners/<int:owner_id>", methods=["PUT"])
def update_owner(owner_id):
    data = parse_body(
        required={"user_id": int, "first_name": str, "last_name": str, "email": str},
    )
    _require_self(data["user_id"], owner_id)
    owner = owner_repository.update(
        owner_id=owner_id,
        first_name=data["first_name"],
        last_name=data["last_name"],
        email=data["email"],
    )
    return jsonify(owner.to_dict())


@owner_bp.route("/owners/<int:owner_id>", methods=["DELETE"])
def delete_owner(owner_id):
    _require_self(require_query_int("user_id"), owner_id)
    owner_repository.delete(owner_id)
    return "", 204