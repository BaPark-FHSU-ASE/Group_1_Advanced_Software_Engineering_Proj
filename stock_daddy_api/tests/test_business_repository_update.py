from app.db.connection import get_connection
from app.models.business import Business


def test_update_changes_and_returns_business():
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO business (name, owner_id) VALUES (?, ?)",
            ("Before Update Biz", 1),
        )
        business_id = cursor.lastrowid

        conn.execute(
            "UPDATE business SET name = ?, owner_id = ? WHERE business_id = ?",
            ("After Update Biz", 1, business_id),
        )
        row = conn.execute(
            "SELECT * FROM business WHERE business_id = ?", (business_id,)
        ).fetchone()
        business = Business.from_row(row)

        assert business.name == "After Update Biz"
        assert business.owner_id == 1
    finally:
        conn.rollback()
        conn.close()