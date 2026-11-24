from app.db.connection import get_connection
from app.models.item import Item



_MY_STORAGE_UNITS = (
    "SELECT storage_id FROM storage WHERE room_id IN "
    "(SELECT room_id FROM room WHERE building_id IN "
    "(SELECT building_id FROM building WHERE business_id IN "
    "(SELECT business_id FROM business_member WHERE owner_id = ?)))"
)

_LAST_KNOWN_STORAGE = (
    "SELECT COALESCE(m.from_storage_id, m.to_storage_id) FROM item_movement m "
    "WHERE m.item_id = item.item_id "
    "AND (m.from_storage_id IS NOT NULL OR m.to_storage_id IS NOT NULL) "
    "ORDER BY m.moved_at DESC, m.item_movement_id DESC LIMIT 1"
)


def get_all(include_retired=False, user_id=None):
    sql = "SELECT * FROM item WHERE 1 = 1"
    params = []
    if not include_retired:
        sql += " AND retired IS NULL"
    if user_id is not None:
        sql += (
            f" AND (storage_id IN ({_MY_STORAGE_UNITS})"
            f" OR (storage_id IS NULL AND ({_LAST_KNOWN_STORAGE}) IN ({_MY_STORAGE_UNITS})))"
        )
        params += [user_id, user_id]

    conn = get_connection()
    rows = conn.execute(sql, params).fetchall()
    conn.close()

    return [Item.from_row(row) for row in rows]


def create(item_type_id, storage_id, item_name, item_status="In Storage"):
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO item (item_type_id, storage_id, item_name, item_status) VALUES (?, ?, ?, ?)",
        (item_type_id, storage_id, item_name, item_status),
    )
    conn.commit()

    new_item_id = cursor.lastrowid
    row = conn.execute(
        "SELECT * FROM item WHERE item_id = ?", (new_item_id,)
    ).fetchone()
    conn.close()

    return Item.from_row(row)


def create_many(item_type_id, storage_id, item_names):
    conn = get_connection()
    try:
        item_ids = []
        for item_name in item_names:
            cursor = conn.execute(
                "INSERT INTO item (item_type_id, storage_id, item_name, item_status) "
                "VALUES (?, ?, ?, 'In Storage')",
                (item_type_id, storage_id, item_name),
            )
            conn.execute(
                "INSERT INTO item_movement (item_id, from_storage_id, to_storage_id) "
                "VALUES (?, NULL, ?)",
                (cursor.lastrowid, storage_id),
            )
            item_ids.append(cursor.lastrowid)
        conn.commit()
        return item_ids
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def count_of_type(item_type_id):
    conn = get_connection()
    try:
        return conn.execute(
            "SELECT COUNT(*) FROM item WHERE item_type_id = ?", (item_type_id,)
        ).fetchone()[0]
    finally:
        conn.close()


def get_by_id(item_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM item WHERE item_id = ?", (item_id,)
    ).fetchone()
    conn.close()

    if row is None:
        return None

    return Item.from_row(row)


def update(item_id, item_type_id, storage_id, item_name, item_status):
    conn = get_connection()
    conn.execute(
        "UPDATE item SET item_type_id = ?, storage_id = ?, item_name = ?, item_status = ? WHERE item_id = ?",
        (item_type_id, storage_id, item_name, item_status, item_id),
    )
    conn.commit()

    row = conn.execute(
        "SELECT * FROM item WHERE item_id = ?", (item_id,)
    ).fetchone()
    conn.close()

    if row is None:
        return None

    return Item.from_row(row)


def change_status(item_id, old_status, old_storage_id, new_status, new_storage_id):
    conn = get_connection()
    try:
        cursor = conn.execute(
            "UPDATE item SET item_status = ?, storage_id = ? "
            "WHERE item_id = ? AND item_status = ?",
            (new_status, new_storage_id, item_id, old_status),
        )
        if cursor.rowcount == 0:
            conn.rollback()
            return False

        moved = new_storage_id != old_storage_id
        conn.execute(
            "INSERT INTO item_movement "
            "(item_id, from_storage_id, to_storage_id, from_status, to_status) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                item_id,
                old_storage_id if moved else None,
                new_storage_id if moved else None,
                old_status,
                new_status,
            ),
        )
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def delete(item_id):
    conn = get_connection()
    cursor = conn.execute("DELETE FROM item WHERE item_id = ?", (item_id,))
    conn.commit()
    conn.close()

    return cursor.rowcount > 0