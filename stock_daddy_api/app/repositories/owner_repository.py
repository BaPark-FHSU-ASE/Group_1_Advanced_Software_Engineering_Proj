from app.db.connection import get_connection
from app.models.owner import Owner

# Get all owners
def get_all():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM owners").fetchall()
    conn.close()

    return [Owner.from_row(row) for row in rows]

def create(first_name, last_name, email, password_hash):
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO owners (first_name, last_name, email, password_hash) "
        "VALUES (?, ?, ?, ?)",
        (first_name, last_name, email, password_hash),
    )
    conn.commit()

    new_owner_id = cursor.lastrowid
    row = conn.execute(
        "SELECT * FROM owners WHERE owner_id = ?", (new_owner_id,)
    ).fetchone()
    conn.close()

    return Owner.from_row(row)