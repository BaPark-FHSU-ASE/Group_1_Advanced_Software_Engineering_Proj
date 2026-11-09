from app.db.connection import get_connection
from app.models.owner import Owner


def get_all(user_id=None):
    sql = "SELECT * FROM owners"
    params = []
    if user_id is not None:
        sql += (
            " WHERE owner_id = ? OR owner_id IN (SELECT owner_id FROM business_member "
            "WHERE business_id IN (SELECT business_id FROM business_member WHERE owner_id = ?))"
        )
        params = [user_id, user_id]

    conn = get_connection()
    rows = conn.execute(sql, params).fetchall()
    conn.close()

    return [Owner.from_row(row) for row in rows]

# Create an owner
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
# Gen an owner by Id
def get_by_id(owner_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM owners WHERE owner_id = ?", (owner_id,)
    ).fetchone()
    conn.close()

    if row is None:
        return None

    return Owner.from_row(row)

# Find a person by email 
def get_by_email(email):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM owners WHERE lower(email) = lower(?)", (email,)
    ).fetchone()
    conn.close()

    if row is None:
        return None

    return Owner.from_row(row)

def update(owner_id, first_name, last_name, email):
    conn = get_connection()
    conn.execute(
        "UPDATE owners SET first_name = ?, last_name = ?, email = ? WHERE owner_id = ?",
        (first_name, last_name, email, owner_id),
    )
    conn.commit()

    row = conn.execute(
        "SELECT * FROM owners WHERE owner_id = ?", (owner_id,)
    ).fetchone()
    conn.close()

    if row is None:
        return None

    return Owner.from_row(row)

def delete(owner_id):
    conn = get_connection()
    cursor = conn.execute("DELETE FROM owners WHERE owner_id = ?", (owner_id,))
    conn.commit()
    conn.close()

    return cursor.rowcount > 0

