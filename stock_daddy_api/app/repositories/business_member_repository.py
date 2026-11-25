from app.db.connection import get_connection
from app.models.business_member import BusinessMember


_MEMBER_WITH_PERSON = (
    "SELECT bm.business_member_id, bm.business_id, bm.owner_id, bm.role, "
    "o.first_name, o.last_name, o.email "
    "FROM business_member bm JOIN owners o ON o.owner_id = bm.owner_id"
)


def get_all(business_id=None):
    conn = get_connection()
    try:
        if business_id is None:
            rows = conn.execute(
                _MEMBER_WITH_PERSON + " ORDER BY bm.business_member_id"
            ).fetchall()
        else:
            rows = conn.execute(
                _MEMBER_WITH_PERSON + " WHERE bm.business_id = ? "
                "ORDER BY bm.business_member_id",
                (business_id,),
            ).fetchall()
    finally:
        conn.close()

    return [BusinessMember.from_row(row) for row in rows]


def get_by_id(business_member_id):
    conn = get_connection()
    try:
        row = conn.execute(
            _MEMBER_WITH_PERSON + " WHERE bm.business_member_id = ?",
            (business_member_id,),
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        return None

    return BusinessMember.from_row(row)


def get_role(business_id, owner_id):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT role FROM business_member WHERE business_id = ? AND owner_id = ?",
            (business_id, owner_id),
        ).fetchone()
    finally:
        conn.close()

    return None if row is None else row["role"]

def has_role_anywhere(owner_id, role=None):
    sql = "SELECT 1 FROM business_member WHERE owner_id = ?"
    params = [owner_id]
    if role is not None:
        sql += " AND role = ?"
        params.append(role)

    conn = get_connection()
    try:
        row = conn.execute(sql + " LIMIT 1", params).fetchone()
    finally:
        conn.close()

    return row is not None

def get_memberships(owner_id):
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT bm.business_id, bm.role FROM business_member bm "
            "JOIN business b ON b.business_id = bm.business_id "
            "WHERE bm.owner_id = ? AND b.retired IS NULL "
            "ORDER BY bm.business_id",
            (owner_id,),
        ).fetchall()
    finally:
        conn.close()

    return [{"business_id": row["business_id"], "role": row["role"]} for row in rows]


def share_a_business(owner_id, other_id):

    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT 1 FROM business_member a "
            "JOIN business_member b ON b.business_id = a.business_id "
            "WHERE a.owner_id = ? AND b.owner_id = ? LIMIT 1",
            (owner_id, other_id),
        ).fetchone()
    finally:
        conn.close()

    return row is not None

def count_owners(business_id):

    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM business_member "
            "WHERE business_id = ? AND role = 'owner'",
            (business_id,),
        ).fetchone()
    finally:
        conn.close()

    return row["n"]


def add(business_id, owner_id, role):
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO business_member (business_id, owner_id, role) VALUES (?, ?, ?)",
            (business_id, owner_id, role),
        )
        conn.commit()
        row = conn.execute(
            _MEMBER_WITH_PERSON + " WHERE bm.business_member_id = ?",
            (cursor.lastrowid,),
        ).fetchone()
    finally:
        conn.close()

    return BusinessMember.from_row(row)


def update_role(business_member_id, role):
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE business_member SET role = ? WHERE business_member_id = ?",
            (role, business_member_id),
        )
        conn.commit()
        row = conn.execute(
            _MEMBER_WITH_PERSON + " WHERE bm.business_member_id = ?",
            (business_member_id,),
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        return None

    return BusinessMember.from_row(row)


def remove(business_member_id):
    conn = get_connection()
    try:
        cursor = conn.execute(
            "DELETE FROM business_member WHERE business_member_id = ?",
            (business_member_id,),
        )
        conn.commit()
    finally:
        conn.close()

    return cursor.rowcount > 0