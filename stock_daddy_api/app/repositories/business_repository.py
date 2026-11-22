from app.db.connection import get_connection
from app.models.business import Business


def get_all(include_retired=False, user_id=None):

    sql = "SELECT * FROM business WHERE 1 = 1"
    params = []
    if not include_retired:
        sql += " AND retired IS NULL"
    if user_id is not None:
        sql += " AND business_id IN (SELECT business_id FROM business_member WHERE owner_id = ?)"
        params.append(user_id)

    conn = get_connection()
    rows = conn.execute(sql, params).fetchall()
    conn.close()

    return [Business.from_row(row) for row in rows]


def create(name, owner_id):
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO business (name, owner_id) VALUES (?, ?)",
            (name, owner_id),
        )
        new_business_id = cursor.lastrowid

        conn.execute(
            "INSERT INTO business_member (business_id, owner_id, role) "
            "VALUES (?, ?, 'owner')",
            (new_business_id, owner_id),
        )
        conn.commit()

        row = conn.execute(
            "SELECT * FROM business WHERE business_id = ?", (new_business_id,)
        ).fetchone()
    finally:
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
    try:
        conn.execute("DELETE FROM business_member WHERE business_id = ?", (business_id,))
        cursor = conn.execute("DELETE FROM business WHERE business_id = ?", (business_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return cursor.rowcount > 0