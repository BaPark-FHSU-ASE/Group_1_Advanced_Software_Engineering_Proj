"""
Database connection layer for the Stock Daddy frontend.

Wraps schema_v4.sql (Schema_versions/schema_v4.sql) — see that file and
PROJECT root README for setup. Connection config comes from environment
variables so nobody has to hardcode their local MySQL password into a
file that gets committed:

    DB_HOST      default "localhost"
    DB_PORT      default 3306
    DB_USER      default "root"
    DB_PASSWORD  default "" (matches the team's --initialize-insecure setup)
    DB_NAME      default "inventory_management"

Requires schema_v5.sql or later — v5 added owners.email/password_hash,
which register_owner()/verify_owner() below depend on. Passwords are never
stored or compared in plaintext: generate_password_hash/check_password_hash
(werkzeug, scrypt-based) handle both directions.
"""

import os
import pymysql
import pymysql.cursors
from werkzeug.security import generate_password_hash, check_password_hash


def get_connection():
    return pymysql.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        port=int(os.environ.get("DB_PORT", 3306)),
        user=os.environ.get("DB_USER", "root"),
        password=os.environ.get("DB_PASSWORD", ""),
        database=os.environ.get("DB_NAME", "inventory_management"),
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )


class EmailAlreadyRegistered(Exception):
    """Raised by register_owner() when the email is already taken."""
    pass


def register_owner(first_name, last_name, email, password):
    """Create a new owner with a hashed password. Returns the new owner_id.

    Raises EmailAlreadyRegistered if the email is already in use (owners.email
    is UNIQUE — this catches that constraint and re-raises as something the
    route can show a friendly message for, instead of a raw DB error).
    """
    password_hash = generate_password_hash(password)
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    "INSERT INTO owners (first_name, last_name, email, password_hash) "
                    "VALUES (%s, %s, %s, %s)",
                    (first_name, last_name, email, password_hash),
                )
            except pymysql.err.IntegrityError as e:
                # 1062 = Duplicate entry, i.e. the UNIQUE constraint on email.
                if e.args[0] == 1062:
                    raise EmailAlreadyRegistered(email) from e
                raise
            return cur.lastrowid
    finally:
        conn.close()


def verify_owner(email, password):
    """Check email/password against the DB. Returns the owner dict on
    success (with first_name, for the session), or None on failure.

    Deliberately returns the same None for "no such email" and "wrong
    password" - not distinguishing the two in the response is what stops
    this endpoint from being usable to enumerate registered emails.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT owner_id, first_name, last_name, password_hash "
                "FROM owners WHERE email = %s",
                (email,),
            )
            owner = cur.fetchone()
        if owner is None:
            return None
        if not check_password_hash(owner["password_hash"], password):
            return None
        return {
            "owner_id": owner["owner_id"],
            "first_name": owner["first_name"],
            "last_name": owner["last_name"],
        }
    finally:
        conn.close()


def get_dashboard_hierarchy():
    """Business -> Building -> Room -> Storage, with item counts per storage.

    Returns a list shaped like app.py's old mock `businesses` list so the
    dashboard template needs no changes.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT business_id, name FROM business ORDER BY business_id")
            businesses = cur.fetchall()

            cur.execute(
                "SELECT building_id, business_id, city, state, street_address "
                "FROM building ORDER BY building_id"
            )
            buildings = cur.fetchall()

            cur.execute(
                "SELECT room_id, building_id, location FROM room ORDER BY room_id"
            )
            rooms = cur.fetchall()

            cur.execute(
                "SELECT s.storage_id, s.room_id, s.storage_type, "
                "       COALESCE(c.item_cnt, 0) AS item_count "
                "FROM storage s "
                "LEFT JOIN v_storage_item_count c ON c.storage_id = s.storage_id "
                "ORDER BY s.storage_id"
            )
            storages = cur.fetchall()

        # Assemble the hierarchy in Python once, rather than one query per level.
        storages_by_room = {}
        for s in storages:
            storages_by_room.setdefault(s["room_id"], []).append({
                "id": s["storage_id"],
                "name": s["storage_type"],  # schema has no separate storage name field
                "type": s["storage_type"],
                "item_count": s["item_count"],
            })

        rooms_by_building = {}
        for r in rooms:
            rooms_by_building.setdefault(r["building_id"], []).append({
                "id": r["room_id"],
                "name": r["location"],
                "storages": storages_by_room.get(r["room_id"], []),
            })

        buildings_by_business = {}
        for b in buildings:
            buildings_by_business.setdefault(b["business_id"], []).append({
                "id": b["building_id"],
                "name": f'{b["city"]} — {b["street_address"]}',
                "address": f'{b["street_address"]}, {b["city"]}, {b["state"]}',
                "rooms": rooms_by_building.get(b["building_id"], []),
            })

        return [
            {
                "id": biz["business_id"],
                "name": biz["name"],
                "buildings": buildings_by_business.get(biz["business_id"], []),
            }
            for biz in businesses
        ]
    finally:
        conn.close()


def get_building(building_id):
    """Building detail + rooms/storages + compliance snapshot for that building."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT building_id, city, state, street_address "
                "FROM building WHERE building_id = %s",
                (building_id,),
            )
            b = cur.fetchone()
            if b is None:
                return None

            cur.execute(
                "SELECT room_id, location FROM room WHERE building_id = %s ORDER BY room_id",
                (building_id,),
            )
            rooms = cur.fetchall()

            cur.execute(
                "SELECT s.storage_id, s.room_id, s.storage_type, "
                "       COALESCE(c.item_cnt, 0) AS item_count "
                "FROM storage s "
                "JOIN room r ON r.room_id = s.room_id "
                "LEFT JOIN v_storage_item_count c ON c.storage_id = s.storage_id "
                "WHERE r.building_id = %s ORDER BY s.storage_id",
                (building_id,),
            )
            storages = cur.fetchall()

            cur.execute(
                "SELECT it.name AS item_type, p.target_qty AS target, "
                "       p.present_qty AS on_hand, p.available_qty AS available, "
                "       (p.present_qty - p.target_qty) AS variance "
                "FROM v_building_item_type_position p "
                "JOIN item_type it ON it.item_type_id = p.item_type_id "
                "WHERE p.building_id = %s "
                "ORDER BY it.name",
                (building_id,),
            )
            compliance = cur.fetchall()

        storages_by_room = {}
        for s in storages:
            storages_by_room.setdefault(s["room_id"], []).append({
                "id": s["storage_id"],
                "name": s["storage_type"],
                "type": s["storage_type"],
                "item_count": s["item_count"],
            })

        return {
            "id": b["building_id"],
            "name": f'{b["city"]} — {b["street_address"]}',
            "address": f'{b["street_address"]}, {b["city"]}, {b["state"]}',
            "rooms": [
                {
                    "id": r["room_id"],
                    "name": r["location"],
                    "storages": storages_by_room.get(r["room_id"], []),
                }
                for r in rooms
            ],
            "compliance": [
                {
                    "item_type": row["item_type"],
                    "target": row["target"],
                    "on_hand": row["on_hand"],
                    "available": row["available"],
                    "variance": row["variance"],
                }
                for row in compliance
            ],
        }
    finally:
        conn.close()


def get_items():
    """All items with their type, status, and full location path."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT i.item_id, i.item_name, it.name AS item_type, i.item_status, "
                "       b.city AS building, r.location AS room, s.storage_type AS storage "
                "FROM item i "
                "JOIN item_type it ON it.item_type_id = i.item_type_id "
                "LEFT JOIN storage s ON s.storage_id = i.storage_id "
                "LEFT JOIN room r ON r.room_id = s.room_id "
                "LEFT JOIN building b ON b.building_id = r.building_id "
                "ORDER BY i.item_id"
            )
            rows = cur.fetchall()
        return [
            {
                "id": row["item_id"],
                "name": row["item_name"],
                "type": row["item_type"],
                "status": row["item_status"],
                # In Transit items have no current storage — show that plainly
                # instead of a blank cell.
                "building": row["building"] or "In transit",
                "room": row["room"] or "—",
                "storage": row["storage"] or "—",
            }
            for row in rows
        ]
    finally:
        conn.close()


def get_item_detail(item_id):
    """Single item + its full movement history, most recent first."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT i.item_id, i.item_name, it.name AS item_type, i.item_status, "
                "       i.date_added, "
                "       b.city AS building, r.location AS room, s.storage_type AS storage "
                "FROM item i "
                "JOIN item_type it ON it.item_type_id = i.item_type_id "
                "LEFT JOIN storage s ON s.storage_id = i.storage_id "
                "LEFT JOIN room r ON r.room_id = s.room_id "
                "LEFT JOIN building b ON b.building_id = r.building_id "
                "WHERE i.item_id = %s",
                (item_id,),
            )
            item = cur.fetchone()
            if item is None:
                return None

            cur.execute(
                "SELECT m.moved_at, "
                "       CONCAT(fb.city, ' / ', fr.location, ' / ', fs.storage_type) AS from_loc, "
                "       CONCAT(tb.city, ' / ', tr.location, ' / ', ts.storage_type) AS to_loc "
                "FROM item_movement m "
                "LEFT JOIN storage fs ON fs.storage_id = m.from_storage_id "
                "LEFT JOIN room fr ON fr.room_id = fs.room_id "
                "LEFT JOIN building fb ON fb.building_id = fr.building_id "
                "LEFT JOIN storage ts ON ts.storage_id = m.to_storage_id "
                "LEFT JOIN room tr ON tr.room_id = ts.room_id "
                "LEFT JOIN building tb ON tb.building_id = tr.building_id "
                "WHERE m.item_id = %s "
                "ORDER BY m.moved_at DESC",
                (item_id,),
            )
            history = cur.fetchall()

        return {
            "id": item["item_id"],
            "name": item["item_name"],
            "type": item["item_type"],
            "status": item["item_status"],
            "building": item["building"] or "In transit",
            "room": item["room"] or "—",
            "storage": item["storage"] or "—",
            "date_added": item["date_added"].strftime("%Y-%m-%d") if item["date_added"] else "—",
            "movement_history": [
                {
                    "date": row["moved_at"].strftime("%Y-%m-%d") if row["moved_at"] else "—",
                    "from": row["from_loc"] or "—",
                    "to": row["to_loc"] or "—",
                }
                for row in history
            ],
        }
    finally:
        conn.close()


def get_compliance_report():
    """Surplus/shortage across every building and item type."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT b.city AS building, it.name AS item_type, "
                "       p.target_qty AS target, p.present_qty AS on_hand, "
                "       p.available_qty AS available, "
                "       (p.present_qty - p.target_qty) AS variance "
                "FROM v_building_item_type_position p "
                "JOIN building b ON b.building_id = p.building_id "
                "JOIN item_type it ON it.item_type_id = p.item_type_id "
                "ORDER BY b.city, it.name"
            )
            rows = cur.fetchall()
        return [
            {
                "building": row["building"],
                "item_type": row["item_type"],
                "target": row["target"],
                "on_hand": row["on_hand"],
                "available": row["available"],
                "variance": row["variance"],
            }
            for row in rows
        ]
    finally:
        conn.close()
