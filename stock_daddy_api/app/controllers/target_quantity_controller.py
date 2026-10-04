from flask import Blueprint, jsonify, request
from app.repositories import target_quantity_repository

target_quantity_bp = Blueprint("target_quantity_bp", __name__)


@target_quantity_bp.route("/target_quantities", methods=["GET"])
def get_target_quantities():
    # Optional ?building_id= filter, e.g. /target_quantities?building_id=1
    building_id = request.args.get("building_id", type=int)
    targets = target_quantity_repository.get_all(building_id=building_id)
    return jsonify([target.to_dict() for target in targets])


@target_quantity_bp.route("/target_quantities/<int:target_quantity_id>", methods=["GET"])
def get_target_quantity(target_quantity_id):
    target = target_quantity_repository.get_by_id(target_quantity_id)
    if target is None:
        return jsonify({"error": "Target quantity not found"}), 404
    return jsonify(target.to_dict())


@target_quantity_bp.route(
    "/target_quantities/<int:building_id>/<int:item_type_id>", methods=["PUT"]
)
def set_target_quantity(building_id, item_type_id):
    """Create or update one building's target for one item type (REQ-15).

    Body: {"owner_id": 1, "target_qty": 5}

    The building has to belong to owner_id. The API has no login of its
    own, so this checks the owner_id the caller sends; it stops the
    frontend from writing to another owner's building, but it trusts
    whoever is calling.
    """
    data = request.get_json(silent=True) or {}
    owner_id = data.get("owner_id")
    target_qty = data.get("target_qty")

    if not isinstance(owner_id, int) or isinstance(owner_id, bool):
        return jsonify({"error": "owner_id is required"}), 400
    if (not isinstance(target_qty, int) or isinstance(target_qty, bool)
            or target_qty < 0):
        return jsonify({"error": "target_qty must be a whole number 0 or more"}), 400

    # Same 404 for "doesn't exist" and "not yours", so ids can't be probed.
    if not target_quantity_repository.building_owned_by(building_id, owner_id):
        return jsonify({"error": "Building not found"}), 404
    if not target_quantity_repository.item_type_exists(item_type_id):
        return jsonify({"error": "Item type not found"}), 404

    target, created = target_quantity_repository.set_target(
        building_id, item_type_id, target_qty
    )
    return jsonify(target.to_dict()), 201 if created else 200


@target_quantity_bp.route("/target_quantities/<int:target_quantity_id>", methods=["DELETE"])
def delete_target_quantity(target_quantity_id):
    deleted = target_quantity_repository.delete(target_quantity_id)
    if not deleted:
        return jsonify({"error": "Target quantity not found"}), 404
    return "", 204
