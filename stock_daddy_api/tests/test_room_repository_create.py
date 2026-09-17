from app.db.connection import get_connection
from app.models.room import Room


def test_create_inserts_and_returns_room():
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO room (building_id, location) VALUES (?, ?)",
            (1, "Test Room"),
        )
        new_room_id = cursor.lastrowid
        row = conn.execute(
            "SELECT * FROM room WHERE room_id = ?", (new_room_id,)
        ).fetchone()
        room = Room.from_row(row)

        assert room.room_id == new_room_id
        assert room.building_id == 1
        assert room.location == "Test Room"
    finally:
        conn.rollback()
        conn.close()