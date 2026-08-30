from app.db.connection import get_connection
from app.repositories import business_repository


def test_delete_removes_business_and_returns_true():
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO business (name, owner_id) VALUES (?, ?)",
            ("Delete Me Biz", 1),
        )
        business_id = cursor.lastrowid
        conn.commit()  # delete() opens its own connection, so this row must be committed for it to see it

        result = business_repository.delete(business_id)

        assert result is True

        row = conn.execute(
            "SELECT * FROM business WHERE business_id = ?", (business_id,)
        ).fetchone()
        assert row is None
    finally:
        conn.rollback()
        conn.close()


def test_delete_returns_false_for_missing_business():
    result = business_repository.delete(999999)

    assert result is False