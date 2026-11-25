import csv
import io
from datetime import datetime

from flask import Blueprint, Response, jsonify, request
from app.Validation_Helper import ValidationError, require_query_int
from app.repositories import item_movement_repository

item_movement_bp = Blueprint("item_movement_bp", __name__)

STATUSES = ("In Storage", "In Use", "In Transit")


CSV_COLUMNS = (
    "movement_id", "date", "item_id", "item_name", "item_type",
    "building", "from", "to", "status_change",
)

_TEXT_COLUMNS = ("item_name", "item_type", "building", "from", "to")
_FORMULA_STARTS = ("=", "+", "-", "@", "\t", "\r")


def _optional_int(name):
    raw = request.args.get(name)
    if raw is None or raw.strip() == "":
        return None
    try:
        return int(raw)
    except ValueError:
        raise ValidationError(f"{name} must be a whole number") from None


def _optional_text(name):
    raw = request.args.get(name)
    if raw is None or raw.strip() == "":
        return None
    return raw.strip()


def _optional_date(name):
    raw = _optional_text(name)
    if raw is None:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError:
        raise ValidationError("Dates must look like 2026-11-24 (year-month-day).") from None


def _search_from_request():
    user_id = require_query_int("user_id")
    status = _optional_text("status")
    if status is not None and status not in STATUSES:
        raise ValidationError("Status must be In Storage, In Use or In Transit.")
    date_from = _optional_date("date_from")
    date_to = _optional_date("date_to")
    if date_from and date_to and date_from > date_to:
        raise ValidationError("The start date can't be after the end date.")

    movements = item_movement_repository.search(
        user_id,
        item_id=_optional_int("item_id"),
        item_type_id=_optional_int("item_type_id"),
        building_id=_optional_int("building_id"),
        status=status,
        date_from=date_from,
        date_to=date_to,
        q=_optional_text("q"),
    )
    return [movement.to_dict() for movement in movements]


def _safe_for_spreadsheet(value):
    if isinstance(value, str) and value.startswith(_FORMULA_STARTS):
        return "'" + value
    return value


@item_movement_bp.route("/movements", methods=["GET"])
def get_movements():
    return jsonify(_search_from_request())


@item_movement_bp.route("/movements/export", methods=["GET"])
def export_movements():
    rows = _search_from_request()
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(CSV_COLUMNS)
    for row in rows:
        writer.writerow([
            _safe_for_spreadsheet(row[column]) if column in _TEXT_COLUMNS else row[column]
            for column in CSV_COLUMNS
        ])
    return Response(out.getvalue(), mimetype="text/csv")
