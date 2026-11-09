from flask import Blueprint, jsonify
from app.Validation_Helper import parse_body, query_flag, require_query_int
from app.access import require_role
from app.retire_helper import retire_record
from app.repositories import business_repository

business_bp = Blueprint("business_bp", __name__)

@business_bp.route("/businesses", methods=["GET"])
def get_businesses():
    user_id = require_query_int("user_id")
    businesses = business_repository.get_all(
        include_retired=query_flag("include_retired"), user_id=user_id
    )
    return jsonify([business.to_dict() for business in businesses])


@business_bp.route("/businesses", methods=["POST"])
def create_business():
    data = parse_body(
        required={"name": str, "owner_id": int},
    )
    business = business_repository.create(
        name=data["name"],
        owner_id=data["owner_id"],
    )
    return jsonify(business.to_dict()), 201


@business_bp.route("/businesses/<int:business_id>", methods=["GET"])
def get_business(business_id):
    require_role(require_query_int("user_id"), business_id)
    business = business_repository.get_by_id(business_id)
    return jsonify(business.to_dict())


@business_bp.route("/businesses/<int:business_id>", methods=["PUT"])
def update_business(business_id):
    data = parse_body(
        required={"user_id": int, "name": str},
    )
    require_role(data["user_id"], business_id, "owner")
    current = business_repository.get_by_id(business_id)
    business = business_repository.update(
        business_id=business_id,
        name=data["name"],
        owner_id=current.owner_id,
    )
    return jsonify(business.to_dict())


@business_bp.route("/businesses/<int:business_id>", methods=["DELETE"])
def delete_business(business_id):
    require_role(require_query_int("user_id"), business_id, "owner")
    business_repository.delete(business_id)
    return "", 204

@business_bp.route("/businesses/<int:business_id>/retire", methods=["POST"])
def retire_business(business_id):
    return retire_record("business", business_id, business_repository)