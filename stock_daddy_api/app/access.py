from app.Validation_Helper import ValidationError
from app.repositories import business_lookup_repository, business_member_repository

# Higher number = more access.
_RANK = {"employee": 1, "owner": 2}


class AccessError(ValidationError):
    """404 if no role found, 403 if employee attempts work that must be owner."""


def require_role(user_id, business_id, role="employee", not_found="Business not found"):

    if role not in _RANK:
        raise ValueError(f"role must be one of {sorted(_RANK)}, got {role!r}")

    actual = business_member_repository.get_role(business_id, user_id)
    if actual is None:
        raise AccessError(not_found, 404)
    if _RANK[actual] < _RANK[role]:
        raise AccessError(f"The {role} role is required", 403)
    return actual

def require_record_role(kind, record_id, user_id, role="employee"):

    not_found = f"{kind.capitalize()} not found"
    business_id = business_lookup_repository.business_id_for(kind, record_id)
    if business_id is None:
        raise AccessError(not_found, 404)
    return require_role(user_id, business_id, role, not_found=not_found)