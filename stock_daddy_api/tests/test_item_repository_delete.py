from app.db.connection import get_connection
from app.repositories import item_repository


def test_delete_removes_item_and_returns_true():
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO item (item_type_id, storage_id, item_name, item_status) VALUES (?, ?, ?, ?)",
            (1, 1, "Delete Me Item", "In Storage"),
        )
        item_id = cursor.lastrowid
        conn.commit()  # delete() opens its own connection, so this row must be committed for it to see it

        result = item_repository.delete(item_id)

        assert result is True

        row = conn.execute(
            "SELECT * FROM item WHERE item_id = ?", (item_id,)
        ).fetchone()
        assert row is None
    finally:
        conn.rollback()
        conn.close()


def test_delete_returns_false_for_missing_item():
    result = item_repository.delete(999999)

    assert result is False