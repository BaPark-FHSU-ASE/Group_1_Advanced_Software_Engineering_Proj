from app.db.connection import get_connection
from app.repositories import owner_repository


def test_delete_removes_owner_and_returns_true():
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO owners (first_name, last_name, email, password_hash) "
            "VALUES (?, ?, ?, ?)",
            ("Delete", "Me", "delete_me@example.com", "fakehash"),
        )
        owner_id = cursor.lastrowid
        conn.commit() 

        result = owner_repository.delete(owner_id)

        assert result is True

        row = conn.execute(
            "SELECT * FROM owners WHERE owner_id = ?", (owner_id,)
        ).fetchone()
        assert row is None
    finally:
        conn.rollback()
        conn.close()


def test_delete_returns_false_for_missing_owner():
    result = owner_repository.delete(999999)

    assert result is False