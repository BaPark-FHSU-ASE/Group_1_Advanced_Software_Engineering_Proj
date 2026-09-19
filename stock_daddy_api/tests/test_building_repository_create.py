from app.db.connection import get_connection
from app.models.building import Building


def test_create_inserts_and_returns_building():
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO building (business_id, state, city, street_address) VALUES (?, ?, ?, ?)",
            (1, "Kansas", "Test City", "123 Test St"),
        )
        new_building_id = cursor.lastrowid
        row = conn.execute(
            "SELECT * FROM building WHERE building_id = ?", (new_building_id,)
        ).fetchone()
        building = Building.from_row(row)

        assert building.building_id == new_building_id
        assert building.business_id == 1
        assert building.state == "Kansas"
        assert building.city == "Test City"
        assert building.street_address == "123 Test St"
    finally:
        conn.rollback()
        conn.close()