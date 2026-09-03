from app.db.connection import get_connection
from app.models.item_type import ItemType


def test_create_inserts_and_returns_item_type():
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO item_type (name, description, replacement_cost) VALUES (?, ?, ?)",
            ("Test Type", "A test item type", 50.00),
        )
        new_item_type_id = cursor.lastrowid
        row = conn.execute(
            "SELECT * FROM item_type WHERE item_type_id = ?", (new_item_type_id,)
        ).fetchone()
        item_type = ItemType.from_row(row)

        assert item_type.item_type_id == new_item_type_id
        assert item_type.name == "Test Type"
        assert item_type.description == "A test item type"
        assert item_type.replacement_cost == 50.00
    finally:
        conn.rollback()
        conn.close()