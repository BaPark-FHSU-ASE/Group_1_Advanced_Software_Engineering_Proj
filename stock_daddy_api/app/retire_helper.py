from flask import jsonify
from app.Validation_Helper import ValidationError, parse_body
from app.access import require_record_role
from app.repositories import retire_repository

_INSIDE_WORDS = [
    ("buildings", "building", "buildings"),
    ("rooms", "room", "rooms"),
    ("storage_units", "storage unit", "storage units"),
    ("items", "item", "items"),
]


def describe_inside(inside):
    """{"storage_units": 2, "items": 21} -> "2 storage units and 21 items"."""
    parts = []
    for key, one, many in _INSIDE_WORDS:
        count = inside.get(key, 0)
        if count:
            parts.append(f"{count} {one if count == 1 else many}")
    if len(parts) > 1:
        return ", ".join(parts[:-1]) + " and " + parts[-1]
    return "".join(parts)


def retire_record(kind, record_id, repository):
    data = parse_body(required={"user_id": int})
    require_record_role(kind, record_id, data["user_id"], "owner")
    outcome, inside = retire_repository.retire(kind, record_id)
    if outcome == retire_repository.NOT_EMPTY:
        message = f"Can't retire this {kind}: {describe_inside(inside)} still inside"
        return jsonify({"error": message, "still_inside": inside}), 409

    return jsonify(repository.get_by_id(record_id).to_dict())



_PARENT_WORDS = {
    "business": "business",
    "building": "building",
    "room": "room",
    "storage": "storage unit",
}


def require_not_retired(kind, record_id):
    if retire_repository.is_retired(kind, record_id):
        raise ValidationError(f"That {_PARENT_WORDS[kind]} is retired", 409)