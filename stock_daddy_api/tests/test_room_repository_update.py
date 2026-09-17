from app.db.connection import get_connection
from app.models.room import Room


def test_update_changes_and_returns_room():
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO room (building_id, location) VALUES (?, ?)",
            (1, "Before Update Room"),
        )
        room_id = cursor.lastrowid

        conn.execute(
            "UPDATE room SET building_id = ?, location = ? WHERE room_id = ?",
            (1, "After Update Room", room_id),
        )
        row = conn.execute(
            "SELECT * FROM room WHERE room_id = ?", (room_id,)
        ).fetchone()
        room = Room.from_row(row)

        assert room.location == "After Update Room"
    finally:
        conn.rollback()
        conn.close()