from flask import Blueprint, jsonify

from app import plan_builder
from app.access import AccessError
from app.repositories import business_member_repository
from app.Validation_Helper import parse_body

plan_bp = Blueprint("plan_bp", __name__)


@plan_bp.route("/plans", methods=["POST"])
def create_plan():
    """Run the optimizer over everything the user owns (REQ-18 to REQ-24).

    Body: {"user_id": 1}

    Owners only. An employee gets a 403. Someone who isn't part of any
    business just gets an empty plan, since there's nothing of theirs to
    move. If a shortage can't be filled by transfer or by buying new, the
    answer is a 409 with a sentence saying which one.
    """
    user_id = parse_body(required={"user_id": int})["user_id"]

    is_owner = business_member_repository.has_role_anywhere(user_id, "owner")
    if not is_owner and business_member_repository.has_role_anywhere(user_id):
        raise AccessError("The owner role is required to run a plan", 403)

    return jsonify(plan_builder.generate_plan(user_id))
