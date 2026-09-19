from flask import Blueprint, jsonify, request
from app.repositories import room_repository

room_bp = Blueprint("room_bp", __name__)


@room_bp.route("/rooms", methods=["GET"])
def get_rooms():
    rooms = room_repository.get_all()
    return jsonify([room.to_dict() for room in rooms])


@room_bp.route("/rooms", methods=["POST"])
def create_room():
    data = request.get_json()
    room = room_repository.create(
        building_id=data["building_id"],
        location=data["location"],
    )
    return jsonify(room.to_dict()), 201


@room_bp.route("/rooms/<int:room_id>", methods=["GET"])
def get_room(room_id):
    room = room_repository.get_by_id(room_id)
    if room is None:
        return jsonify({"error": "Room not found"}), 404
    return jsonify(room.to_dict())


@room_bp.route("/rooms/<int:room_id>", methods=["PUT"])
def update_room(room_id):
    data = request.get_json()
    room = room_repository.update(
        room_id=room_id,
        building_id=data["building_id"],
        location=data["location"],
    )
    if room is None:
        return jsonify({"error": "Room not found"}), 404
    return jsonify(room.to_dict())


@room_bp.route("/rooms/<int:room_id>", methods=["DELETE"])
def delete_room(room_id):
    deleted = room_repository.delete(room_id)
    if not deleted:
        return jsonify({"error": "Room not found"}), 404
    return "", 204