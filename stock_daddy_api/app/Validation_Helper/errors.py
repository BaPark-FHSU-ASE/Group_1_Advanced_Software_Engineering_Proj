import sqlite3

from flask import jsonify

from app.Validation_Helper.validation import ValidationError


def describe_integrity_error(error):
    """Map a sqlite3.IntegrityError to (status code, plain message)."""
    text = str(error)
    detail = text.split(":", 1)[1].strip() if ":" in text else ""

    if text.startswith("UNIQUE constraint failed"):
        columns = [part.strip().split(".")[-1] for part in detail.split(",")]
        return 409, f"A record with that {' and '.join(columns)} already exists"
    if text.startswith("FOREIGN KEY constraint failed"):
        return 409, (
            "That record refers to something that doesn't exist, "
            "or other records still depend on it"
        )
    if text.startswith("NOT NULL constraint failed"):
        return 400, f"{detail.split('.')[-1]} is required"
    if text.startswith("CHECK constraint failed"):
        return 400, f"That value is not allowed ({detail})"
    return 400, "The database rejected that data"


def register_error_handlers(app):
    @app.errorhandler(ValidationError)
    def handle_validation_error(error):
        return jsonify({"error": error.message}), error.status_code

    @app.errorhandler(sqlite3.IntegrityError)
    def handle_integrity_error(error):
        status_code, message = describe_integrity_error(error)
        return jsonify({"error": message}), status_code