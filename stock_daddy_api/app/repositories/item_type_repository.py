from app.db.connection import get_connection
from app.models.item_type import ItemType


def get_all():
    """Return every item type in the database as a list of ItemType objects."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM item_type").fetchall()
    conn.close()

    return [ItemType.from_row(row) for row in rows]


def create(name, description, replacement_cost):
    """Insert a new item type and return it as a fully-populated ItemType object."""
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO item_type (name, description, replacement_cost) VALUES (?, ?, ?)",
        (name, description, replacement_cost),
    )
    conn.commit()

    new_item_type_id = cursor.lastrowid
    row = conn.execute(
        "SELECT * FROM item_type WHERE item_type_id = ?", (new_item_type_id,)
    ).fetchone()
    conn.close()

    return ItemType.from_row(row)


def get_by_id(item_type_id):
    """Return one ItemType by ID, or None if no such item type exists."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM item_type WHERE item_type_id = ?", (item_type_id,)
    ).fetchone()
    conn.close()

    if row is None:
        return None

    return ItemType.from_row(row)


def update(item_type_id, name, description, replacement_cost):
    """Update an existing item type's fields and return the updated ItemType, or None if no such item type exists."""
    conn = get_connection()
    conn.execute(
        "UPDATE item_type SET name = ?, description = ?, replacement_cost = ? WHERE item_type_id = ?",
        (name, description, replacement_cost, item_type_id),
    )
    conn.commit()

    row = conn.execute(
        "SELECT * FROM item_type WHERE item_type_id = ?", (item_type_id,)
    ).fetchone()
    conn.close()

    if row is None:
        return None

    return ItemType.from_row(row)


def delete(item_type_id):
    """Delete an item type by ID. Returns True if a row was deleted, False if no such item type existed."""
    conn = get_connection()
    cursor = conn.execute("DELETE FROM item_type WHERE item_type_id = ?", (item_type_id,))
    conn.commit()
    conn.close()

    return cursor.rowcount > 0