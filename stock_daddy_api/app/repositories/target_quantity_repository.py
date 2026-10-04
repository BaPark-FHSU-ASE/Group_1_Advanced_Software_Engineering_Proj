from app.db.connection import get_connection
from app.models.target_quantity import TargetQuantity


def get_all(building_id=None):
    conn = get_connection()
    if building_id is None:
        rows = conn.execute("SELECT * FROM target_quantity").fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM target_quantity WHERE building_id = ?", (building_id,)
        ).fetchall()
    conn.close()

    return [TargetQuantity.from_row(row) for row in rows]


def get_by_id(target_quantity_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM target_quantity WHERE target_quantity_id = ?",
        (target_quantity_id,),
    ).fetchone()
    conn.close()

    if row is None:
        return None

    return TargetQuantity.from_row(row)


def building_owned_by(building_id, owner_id):
    """True if the building exists and belongs to this owner (NF-REQ-12)."""
    conn = get_connection()
    row = conn.execute(
        "SELECT 1 FROM building bl "
        "JOIN business bs ON bs.business_id = bl.business_id "
        "WHERE bl.building_id = ? AND bs.owner_id = ?",
        (building_id, owner_id),
    ).fetchone()
    conn.close()

    return row is not None


def item_type_exists(item_type_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT 1 FROM item_type WHERE item_type_id = ?", (item_type_id,)
    ).fetchone()
    conn.close()

    return row is not None


def set_target(building_id, item_type_id, target_qty):
    """Create or update the target for one building + item type (REQ-15).

    The table is UNIQUE on (building_id, item_type_id), so saving a target
    that already exists updates that row instead of adding a duplicate.
    Returns (TargetQuantity, created) where created is False on an update.
    """
    conn = get_connection()
    existed = conn.execute(
        "SELECT 1 FROM target_quantity WHERE building_id = ? AND item_type_id = ?",
        (building_id, item_type_id),
    ).fetchone() is not None

    conn.execute(
        "INSERT INTO target_quantity (building_id, item_type_id, target_qty) "
        "VALUES (?, ?, ?) "
        "ON CONFLICT (building_id, item_type_id) "
        "DO UPDATE SET target_qty = excluded.target_qty",
        (building_id, item_type_id, target_qty),
    )
    conn.commit()

    row = conn.execute(
        "SELECT * FROM target_quantity WHERE building_id = ? AND item_type_id = ?",
        (building_id, item_type_id),
    ).fetchone()
    conn.close()

    return TargetQuantity.from_row(row), not existed


def delete(target_quantity_id):
    conn = get_connection()
    cursor = conn.execute(
        "DELETE FROM target_quantity WHERE target_quantity_id = ?",
        (target_quantity_id,),
    )
    conn.commit()
    conn.close()

    return cursor.rowcount > 0
