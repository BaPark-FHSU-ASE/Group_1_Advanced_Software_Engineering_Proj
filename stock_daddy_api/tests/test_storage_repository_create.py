from app.db.connection import get_connection
from app.models.storage import Storage


def test_create_inserts_and_returns_storage():
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO storage (room_id, storage_type) VALUES (?, ?)",
            (1, "Test Shelf"),
        )
        new_storage_id = cursor.lastrowid
        row = conn.execute(
            "SELECT * FROM storage WHERE storage_id = ?", (new_storage_id,)
        ).fetchone()
        storage = Storage.from_row(row)

        assert storage.storage_id == new_storage_id
        assert storage.room_id == 1
        assert storage.storage_type == "Test Shelf"
    finally:
        conn.rollback()
        conn.close()