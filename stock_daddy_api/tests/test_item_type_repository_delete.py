from app.db.connection import get_connection
from app.repositories import item_type_repository


def test_delete_removes_item_type_and_returns_true():
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO item_type (name, description, replacement_cost) VALUES (?, ?, ?)",
            ("Delete Me Type", "Delete desc", 5.00),
        )
        item_type_id = cursor.lastrowid
        conn.commit()  # delete() opens its own connection, so this row must be committed for it to see it

        result = item_type_repository.delete(item_type_id)

        assert result is True

        row = conn.execute(
            "SELECT * FROM item_type WHERE item_type_id = ?", (item_type_id,)
        ).fetchone()
        assert row is None
    finally:
        conn.rollback()
        conn.close()


def test_delete_returns_false_for_missing_item_type():
    result = item_type_repository.delete(999999)

    assert result is False