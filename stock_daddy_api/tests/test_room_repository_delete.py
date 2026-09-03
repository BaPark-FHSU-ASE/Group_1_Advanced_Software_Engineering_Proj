from app.db.connection import get_connection
from app.repositories import room_repository


def test_delete_removes_room_and_returns_true():
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO room (building_id, location) VALUES (?, ?)",
            (1, "Delete Me Room"),
        )
        room_id = cursor.lastrowid
        conn.commit()  # delete() opens its own connection, so this row must be committed for it to see it

        result = room_repository.delete(room_id)

        assert result is True

        row = conn.execute(
            "SELECT * FROM room WHERE room_id = ?", (room_id,)
        ).fetchone()
        assert row is None
    finally:
        conn.rollback()
        conn.close()


def test_delete_returns_false_for_missing_room():
    result = room_repository.delete(999999)

    assert result is False