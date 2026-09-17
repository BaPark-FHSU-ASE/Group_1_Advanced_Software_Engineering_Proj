from app.db.connection import get_connection
from app.models.item import Item


def test_update_changes_and_returns_item():
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO item (item_type_id, storage_id, item_name, item_status) VALUES (?, ?, ?, ?)",
            (1, 1, "Before Update Item", "In Storage"),
        )
        item_id = cursor.lastrowid

        conn.execute(
            "UPDATE item SET item_type_id = ?, storage_id = ?, item_name = ?, item_status = ? WHERE item_id = ?",
            (1, 1, "After Update Item", "In Use", item_id),
        )
        row = conn.execute(
            "SELECT * FROM item WHERE item_id = ?", (item_id,)
        ).fetchone()
        item = Item.from_row(row)

        assert item.item_name == "After Update Item"
        assert item.item_status == "In Use"
    finally:
        conn.rollback()
        conn.close()