from app.db.connection import get_connection
from app.models.storage import Storage


def test_update_changes_and_returns_storage():
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO storage (room_id, storage_type) VALUES (?, ?)",
            (1, "Before Update Shelf"),
        )
        storage_id = cursor.lastrowid

        conn.execute(
            "UPDATE storage SET room_id = ?, storage_type = ? WHERE storage_id = ?",
            (1, "After Update Shelf", storage_id),
        )
        row = conn.execute(
            "SELECT * FROM storage WHERE storage_id = ?", (storage_id,)
        ).fetchone()
        storage = Storage.from_row(row)

        assert storage.storage_type == "After Update Shelf"
    finally:
        conn.rollback()
        conn.close()