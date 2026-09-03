from flask import Blueprint, jsonify, request
from app.repositories import building_repository

building_bp = Blueprint("building_bp", __name__)


@building_bp.route("/buildings", methods=["GET"])
def get_buildings():
    buildings = building_repository.get_all()
    return jsonify([building.to_dict() for building in buildings])


@building_bp.route("/buildings", methods=["POST"])
def create_building():
    data = request.get_json()
    building = building_repository.create(
        business_id=data["business_id"],
        state=data["state"],
        city=data["city"],
        street_address=data["street_address"],
    )
    return jsonify(building.to_dict()), 201


@building_bp.route("/buildings/<int:building_id>", methods=["GET"])
def get_building(building_id):
    building = building_repository.get_by_id(building_id)
    if building is None:
        return jsonify({"error": "Building not found"}), 404
    return jsonify(building.to_dict())


@building_bp.route("/buildings/<int:building_id>", methods=["PUT"])
def update_building(building_id):
    data = request.get_json()
    building = building_repository.update(
        building_id=building_id,
        business_id=data["business_id"],
        state=data["state"],
        city=data["city"],
        street_address=data["street_address"],
    )
    if building is None:
        return jsonify({"error": "Building not found"}), 404
    return jsonify(building.to_dict())


@building_bp.route("/buildings/<int:building_id>", methods=["DELETE"])
def delete_building(building_id):
    deleted = building_repository.delete(building_id)
    if not deleted:
        return jsonify({"error": "Building not found"}), 404
    return "", 204