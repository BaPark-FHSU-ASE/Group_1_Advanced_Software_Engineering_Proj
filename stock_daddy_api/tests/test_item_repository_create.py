from app.db.connection import get_connection
from app.models.item import Item


def test_create_inserts_and_returns_item():
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO item (item_type_id, storage_id, item_name, item_status) VALUES (?, ?, ?, ?)",
            (1, 1, "Test Nail Gun", "In Storage"),
        )
        new_item_id = cursor.lastrowid
        row = conn.execute(
            "SELECT * FROM item WHERE item_id = ?", (new_item_id,)
        ).fetchone()
        item = Item.from_row(row)

        assert item.item_id == new_item_id
        assert item.item_type_id == 1
        assert item.storage_id == 1
        assert item.item_name == "Test Nail Gun"
        assert item.item_status == "In Storage"
    finally:
        conn.rollback()
        conn.close()