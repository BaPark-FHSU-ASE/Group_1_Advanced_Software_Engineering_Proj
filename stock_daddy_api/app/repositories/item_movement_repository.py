from app.db.connection import get_connection
from app.models.item_movement import ItemMovement

_MY_STORAGE_UNITS = (
    "SELECT storage_id FROM storage WHERE room_id IN "
    "(SELECT room_id FROM room WHERE building_id IN "
    "(SELECT building_id FROM building WHERE business_id IN "
    "(SELECT business_id FROM business_member WHERE owner_id = ?)))"
)

_LAST_KNOWN_STORAGE = (
    "SELECT COALESCE(m3.from_storage_id, m3.to_storage_id) FROM item_movement m3 "
    "WHERE m3.item_id = i.item_id "
    "AND (m3.from_storage_id IS NOT NULL OR m3.to_storage_id IS NOT NULL) "
    "ORDER BY m3.moved_at DESC, m3.item_movement_id DESC LIMIT 1"
)

_STORAGE_AT_THE_TIME = (
    "COALESCE((SELECT m2.to_storage_id FROM item_movement m2 "
    "WHERE m2.item_id = m.item_id AND m2.to_storage_id IS NOT NULL "
    "AND (m2.moved_at, m2.item_movement_id) <= (m.moved_at, m.item_movement_id) "
    "ORDER BY m2.moved_at DESC, m2.item_movement_id DESC LIMIT 1), i.storage_id)"
)

_SELECT = (
    "SELECT m.item_movement_id, m.moved_at, m.from_status, m.to_status, "
    "i.item_id, i.item_name, it.name AS item_type, "
    "COALESCE(tb.city, fb.city, ab.city) AS building, "
    "(fb.city || ' / ' || fr.location || ' / ' || fs.storage_type) AS from_place, "
    "(tb.city || ' / ' || tr.location || ' / ' || ts.storage_type) AS to_place "
    "FROM item_movement m "
    "JOIN item i ON i.item_id = m.item_id "
    "JOIN item_type it ON it.item_type_id = i.item_type_id "
    "LEFT JOIN storage fs ON fs.storage_id = m.from_storage_id "
    "LEFT JOIN room fr ON fr.room_id = fs.room_id "
    "LEFT JOIN building fb ON fb.building_id = fr.building_id "
    "LEFT JOIN storage ts ON ts.storage_id = m.to_storage_id "
    "LEFT JOIN room tr ON tr.room_id = ts.room_id "
    "LEFT JOIN building tb ON tb.building_id = tr.building_id "
    "LEFT JOIN storage ast ON ast.storage_id = "
    "(CASE WHEN m.from_storage_id IS NULL AND m.to_storage_id IS NULL "
    f"THEN {_STORAGE_AT_THE_TIME} END) "
    "LEFT JOIN room ar ON ar.room_id = ast.room_id "
    "LEFT JOIN building ab ON ab.building_id = ar.building_id "
)


def _like_pattern(text):
    """A LIKE pattern that matches the text anywhere, with % and _ taken literally."""
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def search(user_id, item_id=None, item_type_id=None, building_id=None, status=None,
           date_from=None, date_to=None, q=None):
    sql = (
        _SELECT
        + "WHERE i.retired IS NULL "
        + f"AND (i.storage_id IN ({_MY_STORAGE_UNITS}) "
        + f"OR (i.storage_id IS NULL AND ({_LAST_KNOWN_STORAGE}) IN ({_MY_STORAGE_UNITS}))) "
    )
    params = [user_id, user_id]

    if item_id is not None:
        sql += "AND i.item_id = ? "
        params.append(item_id)
    if item_type_id is not None:
        sql += "AND i.item_type_id = ? "
        params.append(item_type_id)
    if building_id is not None:
        sql += "AND (fb.building_id = ? OR tb.building_id = ? OR ab.building_id = ?) "
        params += [building_id, building_id, building_id]
    if status is not None:
        sql += "AND (m.from_status = ? OR m.to_status = ?) "
        params += [status, status]
    if date_from is not None:
        sql += "AND date(m.moved_at) >= ? "
        params.append(date_from)
    if date_to is not None:
        sql += "AND date(m.moved_at) <= ? "
        params.append(date_to)
    if q is not None:
        sql += "AND i.item_name LIKE ? ESCAPE '\\' "
        params.append(_like_pattern(q))

    sql += "ORDER BY m.moved_at DESC, m.item_movement_id DESC"

    conn = get_connection()
    try:
        rows = conn.execute(sql, params).fetchall()
    finally:
        conn.close()

    return [ItemMovement.from_row(row) for row in rows]
