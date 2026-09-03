from app.db.connection import get_connection
from app.models.item import Item


def get_all():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM item").fetchall()
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


def delete(item_id):
    conn = get_connection()
    cursor = conn.execute("DELETE FROM item WHERE item_id = ?", (item_id,))
    conn.commit()
    conn.close()

    return cursor.rowcount > 0