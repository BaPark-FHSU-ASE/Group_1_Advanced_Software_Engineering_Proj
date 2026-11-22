from app.db.connection import get_connection
from app.models.building import Building


def get_all(include_retired=False, user_id=None):
    sql = "SELECT * FROM building WHERE 1 = 1"
    params = []
    if not include_retired:
        sql += " AND retired IS NULL"
    if user_id is not None:
        sql += (
            " AND business_id IN "
            "(SELECT business_id FROM business_member WHERE owner_id = ?)"
        )
        params.append(user_id)

    conn = get_connection()
    rows = conn.execute(sql, params).fetchall()
    conn.close()

    return [Building.from_row(row) for row in rows]


def create(business_id, state, city, street_address):
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO building (business_id, state, city, street_address) VALUES (?, ?, ?, ?)",
        (business_id, state, city, street_address),
    )
    conn.commit()

    new_building_id = cursor.lastrowid
    row = conn.execute(
        "SELECT * FROM building WHERE building_id = ?", (new_building_id,)
    ).fetchone()
    conn.close()

    return Building.from_row(row)


def get_by_id(building_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM building WHERE building_id = ?", (building_id,)
    ).fetchone()
    conn.close()

    if row is None:
        return None

    return Building.from_row(row)


def update(building_id, business_id, state, city, street_address):
    conn = get_connection()
    conn.execute(
        "UPDATE building SET business_id = ?, state = ?, city = ?, street_address = ? WHERE building_id = ?",
        (business_id, state, city, street_address, building_id),
    )
    conn.commit()

    row = conn.execute(
        "SELECT * FROM building WHERE building_id = ?", (building_id,)
    ).fetchone()
    conn.close()

    if row is None:
        return None

    return Building.from_row(row)


def delete(building_id):
    conn = get_connection()
    cursor = conn.execute("DELETE FROM building WHERE building_id = ?", (building_id,))
    conn.commit()
    conn.close()

    return cursor.rowcount > 0
