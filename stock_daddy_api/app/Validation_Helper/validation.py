

from flask import request


class ValidationError(Exception):
    """A request the API can't accept. errors.py turns it into a JSON 400."""

    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _is_whole_number(value):
    # bool is a subclass of int in Python, so True would slip through
    # without this check.
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_text(value):
    return isinstance(value, str)


# type the route asks for -> (check function, words used in the message)
_TYPES = {
    int: (_is_whole_number, "a whole number"),
    float: (_is_number, "a number"),
    str: (_is_text, "text"),
}


def check_fields(data, required=None, optional=None):
    required = required or {}
    optional = optional or {}
    problems = []
    clean = {}

    for name, kind in required.items():
        value = data.get(name)
        if isinstance(value, str):
            value = value.strip()
        if value is None or value == "":
            problems.append(f"{name} is required")
            continue
        check, words = _TYPES[kind]
        if not check(value):
            problems.append(f"{name} must be {words}")
            continue
        clean[name] = value

    for name, kind in optional.items():
        value = data.get(name)
        if isinstance(value, str):
            value = value.strip()
        if value is None:
            continue
        check, words = _TYPES[kind]
        if not check(value):
            problems.append(f"{name} must be {words}")
            continue
        clean[name] = value

    if problems:
        raise ValidationError("; ".join(problems))
    return clean


def parse_body(required=None, optional=None):
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValidationError("Request body must be a JSON object")
    return check_fields(data, required, optional)



def require_query_int(name):
    raw = request.args.get(name)
    if raw is None or raw.strip() == "":
        raise ValidationError(f"{name} is required")
    try:
        return int(raw)
    except ValueError:
        raise ValidationError(f"{name} must be a whole number") from None
    
    


def query_flag(name):
    raw = request.args.get(name)
    if raw is None:
        return False
    value = raw.strip().lower()
    if value in ("true", "1"):
        return True
    if value in ("false", "0"):
        return False
    raise ValidationError(f"{name} must be true or false")    