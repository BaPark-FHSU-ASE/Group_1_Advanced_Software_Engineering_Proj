from app.db.connection import get_connection
from app.models.business import Business


def get_all():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM business").fetchall()
    conn.close()

    return [Business.from_row(row) for row in rows]


def create(name, owner_id):
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO business (name, owner_id) VALUES (?, ?)",
        (name, owner_id),
    )
    conn.commit()

    new_business_id = cursor.lastrowid
    row = conn.execute(
        "SELECT * FROM business WHERE business_id = ?", (new_business_id,)
    ).fetchone()
    conn.close()

    return Business.from_row(row)


def get_by_id(business_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM business WHERE business_id = ?", (business_id,)
    ).fetchone()
    conn.close()

    if row is None:
        return None

    return Business.from_row(row)


def update(business_id, name, owner_id):
    conn = get_connection()
    conn.execute(
        "UPDATE business SET name = ?, owner_id = ? WHERE business_id = ?",
        (name, owner_id, business_id),
    )
    conn.commit()

    row = conn.execute(
        "SELECT * FROM business WHERE business_id = ?", (business_id,)
    ).fetchone()
    conn.close()

    if row is None:
        return None

    return Business.from_row(row)


def delete(business_id):
    conn = get_connection()
    cursor = conn.execute("DELETE FROM business WHERE business_id = ?", (business_id,))
    conn.commit()
    conn.close()

    return cursor.rowcount > 0