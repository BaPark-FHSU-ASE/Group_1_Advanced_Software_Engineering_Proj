from app.db.connection import get_connection
from app.models.owner import Owner


def test_create_inserts_and_returns_owner():
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO owners (first_name, last_name, email, password_hash) "
            "VALUES (?, ?, ?, ?)",
            ("Test", "Person", "test_create@example.com", "fakehash"),
        )
        new_owner_id = cursor.lastrowid
        row = conn.execute(
            "SELECT * FROM owners WHERE owner_id = ?", (new_owner_id,)
        ).fetchone()
        owner = Owner.from_row(row)

        assert owner.owner_id == new_owner_id
        assert owner.first_name == "Test"
        assert owner.last_name == "Person"
        assert owner.email == "test_create@example.com"
        assert owner.date_added is not None
    finally:
        conn.rollback()
        conn.close()