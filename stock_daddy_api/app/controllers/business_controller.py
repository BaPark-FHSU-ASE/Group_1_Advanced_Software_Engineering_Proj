from flask import Blueprint, jsonify, request
from app.repositories import business_repository

business_bp = Blueprint("business_bp", __name__)


@business_bp.route("/businesses", methods=["GET"])
def get_businesses():
    businesses = business_repository.get_all()
    return jsonify([business.to_dict() for business in businesses])


@business_bp.route("/businesses", methods=["POST"])
def create_business():
    data = request.get_json()
    business = business_repository.create(
        name=data["name"],
        owner_id=data["owner_id"],
    )
    return jsonify(business.to_dict()), 201


@business_bp.route("/businesses/<int:business_id>", methods=["GET"])
def get_business(business_id):
    business = business_repository.get_by_id(business_id)
    if business is None:
        return jsonify({"error": "Business not found"}), 404
    return jsonify(business.to_dict())


@business_bp.route("/businesses/<int:business_id>", methods=["PUT"])
def update_business(business_id):
    data = request.get_json()
    business = business_repository.update(
        business_id=business_id,
        name=data["name"],
        owner_id=data["owner_id"],
    )
    if business is None:
        return jsonify({"error": "Business not found"}), 404
    return jsonify(business.to_dict())


@business_bp.route("/businesses/<int:business_id>", methods=["DELETE"])
def delete_business(business_id):
    deleted = business_repository.delete(business_id)
    if not deleted:
        return jsonify({"error": "Business not found"}), 404
    return "", 204