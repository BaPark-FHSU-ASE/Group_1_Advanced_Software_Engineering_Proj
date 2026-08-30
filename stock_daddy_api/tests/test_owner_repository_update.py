from app.db.connection import get_connection
from app.models.owner import Owner


def test_update_changes_and_returns_owner():
    conn = get_connection()
    try:
        # Insert a throwaway owner to update, rather than touching Dale's
        # real row or one from another test.
        cursor = conn.execute(
            "INSERT INTO owners (first_name, last_name, email, password_hash) "
            "VALUES (?, ?, ?, ?)",
            ("Before", "Update", "before_update@example.com", "fakehash"),
        )
        owner_id = cursor.lastrowid

        conn.execute(
            "UPDATE owners SET first_name = ?, last_name = ?, email = ? WHERE owner_id = ?",
            ("After", "Update", "after_update@example.com", owner_id),
        )
        row = conn.execute(
            "SELECT * FROM owners WHERE owner_id = ?", (owner_id,)
        ).fetchone()
        owner = Owner.from_row(row)

        assert owner.first_name == "After"
        assert owner.last_name == "Update"
        assert owner.email == "after_update@example.com"
    finally:
        conn.rollback()
        conn.close()