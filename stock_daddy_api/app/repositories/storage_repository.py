from app.db.connection import get_connection
from app.models.storage import Storage


def get_all():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM storage").fetchall()
    conn.close()

    return [Storage.from_row(row) for row in rows]


def create(room_id, storage_type):
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO storage (room_id, storage_type) VALUES (?, ?)",
        (room_id, storage_type),
    )
    conn.commit()

    new_storage_id = cursor.lastrowid
    row = conn.execute(
        "SELECT * FROM storage WHERE storage_id = ?", (new_storage_id,)
    ).fetchone()
    conn.close()

    return Storage.from_row(row)


def get_by_id(storage_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM storage WHERE storage_id = ?", (storage_id,)
    ).fetchone()
    conn.close()

    if row is None:
        return None

    return Storage.from_row(row)


def update(storage_id, room_id, storage_type):
    conn = get_connection()
    conn.execute(
        "UPDATE storage SET room_id = ?, storage_type = ? WHERE storage_id = ?",
        (room_id, storage_type, storage_id),
    )
    conn.commit()

    row = conn.execute(
        "SELECT * FROM storage WHERE storage_id = ?", (storage_id,)
    ).fetchone()
    conn.close()

    if row is None:
        return None

    return Storage.from_row(row)


def delete(storage_id):
    conn = get_connection()
    cursor = conn.execute("DELETE FROM storage WHERE storage_id = ?", (storage_id,))
    conn.commit()
    conn.close()

    return cursor.rowcount > 0