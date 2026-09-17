from app.db.connection import get_connection
from app.models.item_type import ItemType


def test_update_changes_and_returns_item_type():
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO item_type (name, description, replacement_cost) VALUES (?, ?, ?)",
            ("Before Update Type", "Before desc", 10.00),
        )
        item_type_id = cursor.lastrowid

        conn.execute(
            "UPDATE item_type SET name = ?, description = ?, replacement_cost = ? WHERE item_type_id = ?",
            ("After Update Type", "After desc", 20.00, item_type_id),
        )
        row = conn.execute(
            "SELECT * FROM item_type WHERE item_type_id = ?", (item_type_id,)
        ).fetchone()
        item_type = ItemType.from_row(row)

        assert item_type.name == "After Update Type"
        assert item_type.replacement_cost == 20.00
    finally:
        conn.rollback()
        conn.close()