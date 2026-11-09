from flask import Blueprint, jsonify
from app.Validation_Helper import parse_body, query_flag, require_query_int
from app.access import require_record_role
from app.retire_helper import require_not_retired, retire_record
from app.repositories import room_repository

room_bp = Blueprint("room_bp", __name__)


room_bp = Blueprint("room_bp", __name__)


@room_bp.route("/rooms", methods=["GET"])
def get_rooms():
    user_id = require_query_int("user_id")
    rooms = room_repository.get_all(
        include_retired=query_flag("include_retired"), user_id=user_id
    )
    return jsonify([room.to_dict() for room in rooms])

@room_bp.route("/rooms", methods=["POST"])
def create_room():
    data = parse_body(
        required={"user_id": int, "building_id": int, "location": str},
    )
    require_record_role("building", data["building_id"], data["user_id"], "owner")
    require_not_retired("building", data["building_id"])
    room = room_repository.create(
        building_id=data["building_id"],
        location=data["location"],
    )
    return jsonify(room.to_dict()), 201


@room_bp.route("/rooms/<int:room_id>", methods=["GET"])
def get_room(room_id):
    require_record_role("room", room_id, require_query_int("user_id"))
    room = room_repository.get_by_id(room_id)
    return jsonify(room.to_dict())


@room_bp.route("/rooms/<int:room_id>", methods=["PUT"])
def update_room(room_id):
    data = parse_body(
        required={"user_id": int, "building_id": int, "location": str},
    )
    # Owner of the room's business now, and of the building it is moving to.
    require_record_role("room", room_id, data["user_id"], "owner")
    require_record_role("building", data["building_id"], data["user_id"], "owner")
    require_not_retired("building", data["building_id"])
    room = room_repository.update(
        room_id=room_id,
        building_id=data["building_id"],
        location=data["location"],
    )
    return jsonify(room.to_dict())


@room_bp.route("/rooms/<int:room_id>", methods=["DELETE"])
def delete_room(room_id):
    require_record_role("room", room_id, require_query_int("user_id"), "owner")
    room_repository.delete(room_id)
    return "", 204

@room_bp.route("/rooms/<int:room_id>/retire", methods=["POST"])
def retire_room(room_id):
    return retire_record("room", room_id, room_repository)