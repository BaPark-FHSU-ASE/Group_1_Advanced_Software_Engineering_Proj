from flask import Blueprint, jsonify
from app.Validation_Helper import parse_body, query_flag, require_query_int
from app.access import require_record_role, require_role
from app.retire_helper import require_not_retired, retire_record
from app.repositories import building_repository

building_bp = Blueprint("building_bp", __name__)

# Who can do what: any member of the business can look at its buildings;
# adding, changing and deleting them is the owner's job.


@building_bp.route("/buildings", methods=["GET"])
def get_buildings():
    user_id = require_query_int("user_id")
    buildings = building_repository.get_all(
        include_retired=query_flag("include_retired"), user_id=user_id
    )
    return jsonify([building.to_dict() for building in buildings])


@building_bp.route("/buildings", methods=["POST"])
def create_building():
    data = parse_body(
        required={"user_id": int, "business_id": int, "state": str, "city": str, "street_address": str},
    )
    require_role(data["user_id"], data["business_id"], "owner")
    require_not_retired("business", data["business_id"])
    building = building_repository.create(
        business_id=data["business_id"],
        state=data["state"],
        city=data["city"],
        street_address=data["street_address"],
    )
    return jsonify(building.to_dict()), 201


@building_bp.route("/buildings/<int:building_id>", methods=["GET"])
def get_building(building_id):
    require_record_role("building", building_id, require_query_int("user_id"))
    building = building_repository.get_by_id(building_id)
    return jsonify(building.to_dict())


@building_bp.route("/buildings/<int:building_id>", methods=["PUT"])
def update_building(building_id):
    data = parse_body(
        required={"user_id": int, "business_id": int, "state": str, "city": str, "street_address": str},
    )
    # Owner of the business it is in now, and of the one it is moving to.
    require_record_role("building", building_id, data["user_id"], "owner")
    require_role(data["user_id"], data["business_id"], "owner")
    require_not_retired("business", data["business_id"])
    building = building_repository.update(
        building_id=building_id,
        business_id=data["business_id"],
        state=data["state"],
        city=data["city"],
        street_address=data["street_address"],
    )
    return jsonify(building.to_dict())


@building_bp.route("/buildings/<int:building_id>", methods=["DELETE"])
def delete_building(building_id):
    require_record_role("building", building_id, require_query_int("user_id"), "owner")
    building_repository.delete(building_id)
    return "", 204


@building_bp.route("/buildings/<int:building_id>/retire", methods=["POST"])
def retire_building(building_id):
    return retire_record("building", building_id, building_repository)
