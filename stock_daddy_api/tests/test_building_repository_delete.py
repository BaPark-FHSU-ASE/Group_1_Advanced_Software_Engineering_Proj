from app.db.connection import get_connection
from app.repositories import building_repository


def test_delete_removes_building_and_returns_true():
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO building (business_id, state, city, street_address) VALUES (?, ?, ?, ?)",
            (1, "Kansas", "Delete Me City", "1 Delete St"),
        )
        building_id = cursor.lastrowid
        conn.commit()  # delete() opens its own connection, so this row must be committed for it to see it

        result = building_repository.delete(building_id)

        assert result is True

        row = conn.execute(
            "SELECT * FROM building WHERE building_id = ?", (building_id,)
        ).fetchone()
        assert row is None
    finally:
        conn.rollback()
        conn.close()


def test_delete_returns_false_for_missing_building():
    result = building_repository.delete(999999)

    assert result is False