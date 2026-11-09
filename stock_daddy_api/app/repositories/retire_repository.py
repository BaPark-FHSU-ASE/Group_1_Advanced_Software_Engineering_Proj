# retire will keep row and history. It will now add a retired timestamp. A record can only be retired once nothing is active inside of it. 
# Generaly, this will mean retiring items, storage unit, then room, then building. All must be done before retiring a business'
from app.db.connection import get_connection

RETIRED = "retired"
ALREADY_RETIRED = "already_retired"
NOT_FOUND = "not_found"
NOT_EMPTY = "not_empty"

# kind -> (table, id column)
_TABLES = {
    "business": ("business", "business_id"),
    "building": ("building", "building_id"),
    "room": ("room", "room_id"),
    "storage": ("storage", "storage_id"),
    "item": ("item", "item_id"),
}


_INSIDE = {
    "business": {
        "buildings": (
            "SELECT COUNT(*) FROM building WHERE business_id = ? AND retired IS NULL"
        ),
        "rooms": (
            "SELECT COUNT(*) FROM room r "
            "JOIN building b ON b.building_id = r.building_id "
            "WHERE b.business_id = ? AND r.retired IS NULL"
        ),
        "storage_units": (
            "SELECT COUNT(*) FROM storage s "
            "JOIN room r ON r.room_id = s.room_id "
            "JOIN building b ON b.building_id = r.building_id "
            "WHERE b.business_id = ? AND s.retired IS NULL"
        ),
        "items": (
            "SELECT COUNT(*) FROM item i "
            "JOIN storage s ON s.storage_id = i.storage_id "
            "JOIN room r ON r.room_id = s.room_id "
            "JOIN building b ON b.building_id = r.building_id "
            "WHERE b.business_id = ? AND i.retired IS NULL"
        ),
    },
    "building": {
        "rooms": "SELECT COUNT(*) FROM room WHERE building_id = ? AND retired IS NULL",
        "storage_units": (
            "SELECT COUNT(*) FROM storage s "
            "JOIN room r ON r.room_id = s.room_id "
            "WHERE r.building_id = ? AND s.retired IS NULL"
        ),
        "items": (
            "SELECT COUNT(*) FROM item i "
            "JOIN storage s ON s.storage_id = i.storage_id "
            "JOIN room r ON r.room_id = s.room_id "
            "WHERE r.building_id = ? AND i.retired IS NULL"
        ),
    },
    "room": {
        "storage_units": (
            "SELECT COUNT(*) FROM storage WHERE room_id = ? AND retired IS NULL"
        ),
        "items": (
            "SELECT COUNT(*) FROM item i "
            "JOIN storage s ON s.storage_id = i.storage_id "
            "WHERE s.room_id = ? AND i.retired IS NULL"
        ),
    },
    "storage": {
        "items": "SELECT COUNT(*) FROM item WHERE storage_id = ? AND retired IS NULL",
    },
    "item": {},
}


# checks what is inside a record prior to retiring
def still_inside(kind, record_id):
 
    queries = _INSIDE[kind]
    conn = get_connection()
    try:
        counts = {
            what: conn.execute(sql, (record_id,)).fetchone()[0]
            for what, sql in queries.items()
        }
    finally:
        conn.close()

    return {what: n for what, n in counts.items() if n > 0}


def retire(kind, record_id):
    table, id_column = _TABLES[kind]

    conn = get_connection()
    try:
        row = conn.execute(
            f"SELECT retired FROM {table} WHERE {id_column} = ?", (record_id,)
        ).fetchone()
        if row is None:
            return NOT_FOUND, {}
        if row["retired"] is not None:
            return ALREADY_RETIRED, {}
    finally:
        conn.close()

    inside = still_inside(kind, record_id)
    if inside:
        return NOT_EMPTY, inside

    conn = get_connection()
    try:
        conn.execute(
            f"UPDATE {table} SET retired = CURRENT_TIMESTAMP "
            f"WHERE {id_column} = ? AND retired IS NULL",
            (record_id,),
        )
        conn.commit()
    finally:
        conn.close()

    return RETIRED, {}

def is_retired(kind, record_id):
   
    table, id_column = _TABLES[kind]
    conn = get_connection()
    try:
        row = conn.execute(
            f"SELECT retired FROM {table} WHERE {id_column} = ?", (record_id,)
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        return None
    return row["retired"] is not None