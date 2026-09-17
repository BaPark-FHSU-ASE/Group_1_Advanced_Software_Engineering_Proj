from app.db.connection import get_connection
from app.models.building import Building


def test_update_changes_and_returns_building():
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO building (business_id, state, city, street_address) VALUES (?, ?, ?, ?)",
            (1, "Kansas", "Before Update City", "1 Before St"),
        )
        building_id = cursor.lastrowid

        conn.execute(
            "UPDATE building SET business_id = ?, state = ?, city = ?, street_address = ? WHERE building_id = ?",
            (1, "Kansas", "After Update City", "2 After St", building_id),
        )
        row = conn.execute(
            "SELECT * FROM building WHERE building_id = ?", (building_id,)
        ).fetchone()
        building = Building.from_row(row)

        assert building.city == "After Update City"
        assert building.street_address == "2 After St"
    finally:
        conn.rollback()
        conn.close()