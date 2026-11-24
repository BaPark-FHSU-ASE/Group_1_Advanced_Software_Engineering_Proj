import re

from flask import Blueprint, jsonify, request
from werkzeug.security import generate_password_hash
from app.Validation_Helper import ValidationError, parse_body, require_query_int
from app.access import AccessError
from app.repositories import business_member_repository, owner_repository

owner_bp = Blueprint("owner_bp", __name__)

MIN_PASSWORD_LENGTH = 8
MAX_NAME_LENGTH = 100
MAX_EMAIL_LENGTH = 255
# Not a full email check, just "something@something.something" with no spaces.
_EMAIL_LOOKS_RIGHT = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _require_can_see(user_id, owner_id):
    if user_id != owner_id and not business_member_repository.share_a_business(user_id, owner_id):
        raise AccessError("Owner not found", 404)


def _require_self(user_id, owner_id):
    _require_can_see(user_id, owner_id)
    if user_id != owner_id:
        raise AccessError("You can only change your own account", 403)


def _account_view(owner):
    """What the login and register answers carry: the person and their businesses."""
    return {
        "owner_id": owner.owner_id,
        "first_name": owner.first_name,
        "last_name": owner.last_name,
        "email": owner.email,
        "memberships": business_member_repository.get_memberships(owner.owner_id),
    }


def _required_text(data, key, label, max_length, problems):
    """A trimmed, non-blank piece of text, or None after adding a plain sentence to problems."""
    value = data.get(key)
    if value is not None and not isinstance(value, str):
        problems.append(f"{label} must be text.")
        return None
    value = (value or "").strip()
    if not value:
        problems.append(f"{label} is required.")
        return None
    if len(value) > max_length:
        problems.append(f"{label} must be {max_length} characters or fewer.")
        return None
    return value


@owner_bp.route("/owners", methods=["GET"])
def get_owners():
    owners = owner_repository.get_all(user_id=require_query_int("user_id"))
    return jsonify([owner.to_dict() for owner in owners])


@owner_bp.route("/auth/register", methods=["POST"])
def register():
    # Written for the person at the screen: the frontend shows these sentences
    # as they are. The password is read without trimming, so spaces in it count.
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValidationError("Request body must be a JSON object")

    problems = []
    first_name = _required_text(data, "first_name", "First name", MAX_NAME_LENGTH, problems)
    last_name = _required_text(data, "last_name", "Last name", MAX_NAME_LENGTH, problems)
    email = _required_text(data, "email", "Email", MAX_EMAIL_LENGTH, problems)
    if email and not _EMAIL_LOOKS_RIGHT.match(email):
        problems.append("Enter a valid email address.")

    password = data.get("password")
    if not isinstance(password, str) or password == "":
        problems.append("Password is required.")
    elif len(password) < MIN_PASSWORD_LENGTH:
        problems.append(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")

    if problems:
        raise ValidationError(" ".join(problems))
    if owner_repository.get_by_email(email) is not None:
        raise ValidationError("An account with that email already exists.", 409)

    owner = owner_repository.create(
        first_name=first_name,
        last_name=last_name,
        email=email,
        password_hash=generate_password_hash(password),
    )
    return jsonify(_account_view(owner)), 201


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