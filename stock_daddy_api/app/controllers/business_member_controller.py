from flask import Blueprint, jsonify
from app.Validation_Helper import ValidationError, parse_body, require_query_int
from app.access import require_role
from app.repositories import business_member_repository, owner_repository

business_member_bp = Blueprint("business_member_bp", __name__)

ROLES = ("owner", "employee")
LAST_OWNER_MESSAGE = "A business needs at least one owner"


def _check_role_value(role):
    if role not in ROLES:
        raise ValidationError("role must be 'owner' or 'employee'")


def _person_to_add(data):
    if ("email" in data) == ("owner_id" in data):
        raise ValidationError("Send either email or owner_id, not both and not neither")
    if "owner_id" in data:
        return data["owner_id"]
    owner = owner_repository.get_by_email(data["email"])
    if owner is None:
        raise ValidationError("No account found with that email", 404)
    return owner.owner_id

def _member_of_business(business_id, member_id):
    """The member, but only if they belong to this business (else None)."""
    member = business_member_repository.get_by_id(member_id)
    if member is None or member.business_id != business_id:
        return None
    return member


def _would_remove_last_owner(member, business_id, new_role=None):
    """True if this change would leave the business with no owner."""
    loses_owner_role = member.role == "owner" and new_role != "owner"
    return loses_owner_role and business_member_repository.count_owners(business_id) <= 1


@business_member_bp.route("/businesses/<int:business_id>/members", methods=["GET"])
def get_members(business_id):
    require_role(require_query_int("user_id"), business_id, "employee")
    members = business_member_repository.get_all(business_id=business_id)
    return jsonify([member.to_dict() for member in members])


@business_member_bp.route("/businesses/<int:business_id>/members", methods=["POST"])
def add_member(business_id):
    data = parse_body(
        required={"user_id": int, "role": str},
        optional={"email": str, "owner_id": int},
    )
    require_role(data["user_id"], business_id, "owner")
    _check_role_value(data["role"])
    person_id = _person_to_add(data)

    member = business_member_repository.add(business_id, person_id, data["role"])
    return jsonify(member.to_dict()), 201


@business_member_bp.route(
    "/businesses/<int:business_id>/members/<int:member_id>", methods=["PUT"]
)
def change_member_role(business_id, member_id):
    data = parse_body(required={"user_id": int, "role": str})
    require_role(data["user_id"], business_id, "owner")
    _check_role_value(data["role"])

    member = _member_of_business(business_id, member_id)
    if member is None:
        return jsonify({"error": "Member not found"}), 404
    if _would_remove_last_owner(member, business_id, new_role=data["role"]):
        return jsonify({"error": LAST_OWNER_MESSAGE}), 409

    updated = business_member_repository.update_role(member_id, data["role"])
    return jsonify(updated.to_dict())


@business_member_bp.route(
    "/businesses/<int:business_id>/members/<int:member_id>", methods=["DELETE"]
)
def remove_member(business_id, member_id):
    require_role(require_query_int("user_id"), business_id, "owner")

    member = _member_of_business(business_id, member_id)
    if member is None:
        return jsonify({"error": "Member not found"}), 404
    if _would_remove_last_owner(member, business_id):
        return jsonify({"error": LAST_OWNER_MESSAGE}), 409

    business_member_repository.remove(member_id)
    return "", 204