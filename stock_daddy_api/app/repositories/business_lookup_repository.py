from app.db.connection import get_connection

_BY_KIND = {
    "business": "SELECT business_id FROM business WHERE business_id = ?",
    "building": "SELECT business_id FROM building WHERE building_id = ?",
    "room": (
        "SELECT b.business_id FROM room r "
        "JOIN building b ON b.building_id = r.building_id "
        "WHERE r.room_id = ?"
    ),
    "storage": (
        "SELECT b.business_id FROM storage s "
        "JOIN room r ON r.room_id = s.room_id "
        "JOIN building b ON b.building_id = r.building_id "
        "WHERE s.storage_id = ?"
    ),
    "item": (
        "SELECT b.business_id FROM item i "
        "JOIN storage s ON s.storage_id = i.storage_id "
        "JOIN room r ON r.room_id = s.room_id "
        "JOIN building b ON b.building_id = r.building_id "
        "WHERE i.item_id = ?"
    ),
}

_ITEM_VIA_LAST_MOVEMENT = (
    "SELECT b.business_id FROM item_movement m "
    "JOIN storage s ON s.storage_id = COALESCE(m.from_storage_id, m.to_storage_id) "
    "JOIN room r ON r.room_id = s.room_id "
    "JOIN building b ON b.building_id = r.building_id "
    "WHERE m.item_id = ? "
    "AND (m.from_storage_id IS NOT NULL OR m.to_storage_id IS NOT NULL) "
    "ORDER BY m.moved_at DESC, m.item_movement_id DESC LIMIT 1"
)

def business_id_for(kind, record_id):
    """The owning business's id, or None if the record (or its trail) is missing."""
    sql = _BY_KIND[kind]
    conn = get_connection()
    try:
        row = conn.execute(sql, (record_id,)).fetchone()
        if row is None and kind == "item":
            row = conn.execute(_ITEM_VIA_LAST_MOVEMENT, (record_id,)).fetchone()
    finally:
        conn.close()

    return None if row is None else row["business_id"]

def businesses_using_item_type(item_type_id):
    sql = (
        "SELECT DISTINCT b.business_id FROM item i "
        "JOIN storage s ON s.storage_id = COALESCE(i.storage_id, ("
        "  SELECT COALESCE(m.from_storage_id, m.to_storage_id) FROM item_movement m "
        "  WHERE m.item_id = i.item_id "
        "  AND (m.from_storage_id IS NOT NULL OR m.to_storage_id IS NOT NULL) "
        "  ORDER BY m.moved_at DESC, m.item_movement_id DESC LIMIT 1)) "
        "JOIN room r ON r.room_id = s.room_id "
        "JOIN building b ON b.building_id = r.building_id "
        "WHERE i.item_type_id = ?"
    )
    conn = get_connection()
    try:
        rows = conn.execute(sql, (item_type_id,)).fetchall()
    finally:
        conn.close()

    return sorted(row["business_id"] for row in rows)