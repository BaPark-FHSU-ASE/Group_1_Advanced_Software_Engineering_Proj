from app.db.connection import get_connection
from app.repositories import storage_repository


def test_delete_removes_storage_and_returns_true():
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO storage (room_id, storage_type) VALUES (?, ?)",
            (1, "Delete Me Shelf"),
        )
        storage_id = cursor.lastrowid
        conn.commit()  # delete() opens its own connection, so this row must be committed for it to see it

        result = storage_repository.delete(storage_id)

        assert result is True

        row = conn.execute(
            "SELECT * FROM storage WHERE storage_id = ?", (storage_id,)
        ).fetchone()
        assert row is None
    finally:
        conn.rollback()
        conn.close()


def test_delete_returns_false_for_missing_storage():
    result = storage_repository.delete(999999)

    assert result is False