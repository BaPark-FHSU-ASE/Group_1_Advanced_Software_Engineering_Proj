
from app.db.connection import get_connection
from app.models.room import Room


def get_all():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM room").fetchall()
    conn.close()

    return [Room.from_row(row) for row in rows]


def create(building_id, location):
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO room (building_id, location) VALUES (?, ?)",
        (building_id, location),
    )
    conn.commit()

    new_room_id = cursor.lastrowid
    row = conn.execute(
        "SELECT * FROM room WHERE room_id = ?", (new_room_id,)
    ).fetchone()
    conn.close()

    return Room.from_row(row)


def get_by_id(room_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM room WHERE room_id = ?", (room_id,)
    ).fetchone()
    conn.close()

    if row is None:
        return None

    return Room.from_row(row)


def update(room_id, building_id, location):
    conn = get_connection()
    conn.execute(
        "UPDATE room SET building_id = ?, location = ? WHERE room_id = ?",
        (building_id, location, room_id),
    )
    conn.commit()

    row = conn.execute(
        "SELECT * FROM room WHERE room_id = ?", (room_id,)
    ).fetchone()
    conn.close()

    if row is None:
        return None

    return Room.from_row(row)


def delete(room_id):
    conn = get_connection()
    cursor = conn.execute("DELETE FROM room WHERE room_id = ?", (room_id,))
    conn.commit()
    conn.close()

    return cursor.rowcount > 0