from app.db.connection import get_connection
from app.models.business import Business


def test_create_inserts_and_returns_business():
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO business (name, owner_id) VALUES (?, ?)",
            ("Test Create Biz", 1),
        )
        new_business_id = cursor.lastrowid
        row = conn.execute(
            "SELECT * FROM business WHERE business_id = ?", (new_business_id,)
        ).fetchone()
        business = Business.from_row(row)

        assert business.business_id == new_business_id
        assert business.name == "Test Create Biz"
        assert business.owner_id == 1
    finally:
        conn.rollback()
        conn.close()