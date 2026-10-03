"""
Database connection layer for the Stock Daddy frontend.

Wraps schema_v5.sql (Schema_versions/schema_v5.sql), running against
SQLite via Python's built-in sqlite3 module — no server to install,
no credentials to configure. The database file (stockdaddy.db, next to
this file) is checked into the repo, built from schema_v5.sql +
seed_data_v5.sql by Schema_versions/build_db.py. If you change the schema
or seed data, re-run that script and commit the resulting .db file.

Passwords are never stored or compared in plaintext: generate_password_hash/
check_password_hash (werkzeug, scrypt-based) handle both directions.

DB_PATH reads from the DB_PATH environment variable, falling back to the
real committed database. This mirrors stock_daddy_api/app/config.py so the
test suite (see tests/conftest.py) can point this module at a disposable
copy instead of the shared file, the same way it's isolated over there.
"""

import os
import sqlite3
from pathlib import Path
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = os.environ.get("DB_PATH") or str(Path(__file__).resolve().parent / "stockdaddy.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    # SQLite does not enforce FOREIGN KEY constraints unless a connection
    # turns it on explicitly - this has to happen on every connection, it
    # is not a one-time database setting.
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn


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
        try:
            cur = conn.execute(
                "INSERT INTO owners (first_name, last_name, email, password_hash) "
                "VALUES (?, ?, ?, ?)",
                (first_name, last_name, email, password_hash),
            )
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed: owners.email" in str(e):
                raise EmailAlreadyRegistered(email) from e
            raise
        conn.commit()
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
        owner = conn.execute(
            "SELECT owner_id, first_name, last_name, password_hash "
            "FROM owners WHERE email = ?",
            (email,),
        ).fetchone()
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


# ---------------------------------------------------------------------------
# Owner filtering (NF-REQ-12)
#
# Every read below takes the logged-in owner's id and only returns that
# owner's records. Ownership comes from the hierarchy:
# business.owner_id -> building -> room -> storage -> item.
# ---------------------------------------------------------------------------

# An item's last known storage unit: where it is now, or, while it's In
# Transit (storage_id is NULL), where its most recent movement left from.
# Without this, In Transit items would belong to nobody and disappear from
# their owner's lists. The item table has no owner column, so this is the
# only way to trace an In Transit item back to its owner.
_ITEM_LAST_STORAGE_SQL = (
    "COALESCE(i.storage_id, ("
    "  SELECT COALESCE(m.to_storage_id, m.from_storage_id) FROM item_movement m "
    "  WHERE m.item_id = i.item_id "
    "    AND (m.to_storage_id IS NOT NULL OR m.from_storage_id IS NOT NULL) "
    "  ORDER BY m.moved_at DESC, m.item_movement_id DESC LIMIT 1"
    "))"
)

# Joins that end at the owning business (alias `obs`) for an item aliased `i`.
_ITEM_OWNER_JOINS = (
    f"JOIN storage os ON os.storage_id = {_ITEM_LAST_STORAGE_SQL} "
    "JOIN room ort ON ort.room_id = os.room_id "
    "JOIN building obl ON obl.building_id = ort.building_id "
    "JOIN business obs ON obs.business_id = obl.business_id "
)


def get_dashboard_hierarchy(owner_id):
    """Business -> Building -> Room -> Storage, with item counts per storage,
    for one owner's businesses only.

    Returns a list shaped like app.py's old mock `businesses` list so the
    dashboard template needs no changes.
    """
    conn = get_connection()
    try:
        businesses = conn.execute(
            "SELECT business_id, name FROM business WHERE owner_id = ? "
            "ORDER BY business_id",
            (owner_id,),
        ).fetchall()

        buildings = conn.execute(
            "SELECT bl.building_id, bl.business_id, bl.city, bl.state, bl.street_address "
            "FROM building bl "
            "JOIN business bs ON bs.business_id = bl.business_id "
            "WHERE bs.owner_id = ? ORDER BY bl.building_id",
            (owner_id,),
        ).fetchall()

        rooms = conn.execute(
            "SELECT r.room_id, r.building_id, r.location FROM room r "
            "JOIN building bl ON bl.building_id = r.building_id "
            "JOIN business bs ON bs.business_id = bl.business_id "
            "WHERE bs.owner_id = ? ORDER BY r.room_id",
            (owner_id,),
        ).fetchall()

        storages = conn.execute(
            "SELECT s.storage_id, s.room_id, s.storage_type, "
            "       COALESCE(c.item_cnt, 0) AS item_count "
            "FROM storage s "
            "JOIN room r ON r.room_id = s.room_id "
            "JOIN building bl ON bl.building_id = r.building_id "
            "JOIN business bs ON bs.business_id = bl.business_id "
            "LEFT JOIN v_storage_item_count c ON c.storage_id = s.storage_id "
            "WHERE bs.owner_id = ? ORDER BY s.storage_id",
            (owner_id,),
        ).fetchall()

        # How many item types each building is short on, for the red badge
        # on its Dashboard card (same numbers as the Surplus & Shortage page).
        shortages = dict(conn.execute(
            "SELECT p.building_id, COUNT(*) FROM v_building_item_type_position p "
            "JOIN building bl ON bl.building_id = p.building_id "
            "JOIN business bs ON bs.business_id = bl.business_id "
            "WHERE bs.owner_id = ? AND p.shortage_qty > 0 "
            "GROUP BY p.building_id",
            (owner_id,),
        ).fetchall())

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
            b_rooms = rooms_by_building.get(b["building_id"], [])
            b_storages = [st for r in b_rooms for st in r["storages"]]
            buildings_by_business.setdefault(b["business_id"], []).append({
                "id": b["building_id"],
                "name": f'{b["city"]} — {b["street_address"]}',
                "address": f'{b["street_address"]}, {b["city"]}, {b["state"]}',
                "rooms": b_rooms,
                # Summary numbers for the Dashboard card
                "room_count": len(b_rooms),
                "storage_count": len(b_storages),
                "item_count": sum(st["item_count"] for st in b_storages),
                "shortage_count": shortages.get(b["building_id"], 0),
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


def get_building(owner_id, building_id):
    """Building detail + rooms/storages + compliance snapshot for that building.

    Returns None if the building doesn't exist or belongs to another owner;
    the route treats both the same, so ids can't be probed (NF-REQ-12).
    """
    conn = get_connection()
    try:
        b = conn.execute(
            "SELECT bl.building_id, bl.city, bl.state, bl.street_address "
            "FROM building bl "
            "JOIN business bs ON bs.business_id = bl.business_id "
            "WHERE bl.building_id = ? AND bs.owner_id = ?",
            (building_id, owner_id),
        ).fetchone()
        if b is None:
            return None

        rooms = conn.execute(
            "SELECT room_id, location FROM room WHERE building_id = ? ORDER BY room_id",
            (building_id,),
        ).fetchall()

        storages = conn.execute(
            "SELECT s.storage_id, s.room_id, s.storage_type, "
            "       COALESCE(c.item_cnt, 0) AS item_count "
            "FROM storage s "
            "JOIN room r ON r.room_id = s.room_id "
            "LEFT JOIN v_storage_item_count c ON c.storage_id = s.storage_id "
            "WHERE r.building_id = ? ORDER BY s.storage_id",
            (building_id,),
        ).fetchall()

        compliance = conn.execute(
            "SELECT it.name AS item_type, p.target_qty AS target, "
            "       p.present_qty AS on_hand, p.available_qty AS available, "
            "       (p.present_qty - p.target_qty) AS variance "
            "FROM v_building_item_type_position p "
            "JOIN item_type it ON it.item_type_id = p.item_type_id "
            "WHERE p.building_id = ? "
            "ORDER BY it.name",
            (building_id,),
        ).fetchall()

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


def get_items(owner_id):
    """All of one owner's items with their type, status, and location path."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT i.item_id, i.item_name, it.name AS item_type, i.item_status, "
            "       b.city AS building, r.location AS room, s.storage_type AS storage "
            "FROM item i "
            "JOIN item_type it ON it.item_type_id = i.item_type_id "
            "LEFT JOIN storage s ON s.storage_id = i.storage_id "
            "LEFT JOIN room r ON r.room_id = s.room_id "
            "LEFT JOIN building b ON b.building_id = r.building_id "
            + _ITEM_OWNER_JOINS +
            "WHERE obs.owner_id = ? "
            "ORDER BY i.item_id",
            (owner_id,),
        ).fetchall()
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


def get_item_detail(owner_id, item_id):
    """Single item + its full movement history, most recent first.

    Returns None if the item doesn't exist or belongs to another owner.
    """
    conn = get_connection()
    try:
        item = conn.execute(
            "SELECT i.item_id, i.item_name, it.name AS item_type, i.item_status, "
            "       i.storage_id, i.date_added, "
            "       b.city AS building, r.location AS room, s.storage_type AS storage "
            "FROM item i "
            "JOIN item_type it ON it.item_type_id = i.item_type_id "
            "LEFT JOIN storage s ON s.storage_id = i.storage_id "
            "LEFT JOIN room r ON r.room_id = s.room_id "
            "LEFT JOIN building b ON b.building_id = r.building_id "
            + _ITEM_OWNER_JOINS +
            "WHERE i.item_id = ? AND obs.owner_id = ?",
            (item_id, owner_id),
        ).fetchone()
        if item is None:
            return None

        history = conn.execute(
            "SELECT m.moved_at, m.from_status, m.to_status, "
            "       (fb.city || ' / ' || fr.location || ' / ' || fs.storage_type) AS from_loc, "
            "       (tb.city || ' / ' || tr.location || ' / ' || ts.storage_type) AS to_loc "
            "FROM item_movement m "
            "LEFT JOIN storage fs ON fs.storage_id = m.from_storage_id "
            "LEFT JOIN room fr ON fr.room_id = fs.room_id "
            "LEFT JOIN building fb ON fb.building_id = fr.building_id "
            "LEFT JOIN storage ts ON ts.storage_id = m.to_storage_id "
            "LEFT JOIN room tr ON tr.room_id = ts.room_id "
            "LEFT JOIN building tb ON tb.building_id = tr.building_id "
            "WHERE m.item_id = ? "
            "ORDER BY m.moved_at DESC, m.item_movement_id DESC",
            (item_id,),
        ).fetchall()

        return {
            "id": item["item_id"],
            "name": item["item_name"],
            "type": item["item_type"],
            "status": item["item_status"],
            "building": item["building"] or "In transit",
            "room": item["room"] or "—",
            "storage": item["storage"] or "—",
            "storage_id": item["storage_id"],
            "date_added": (item["date_added"] or "—")[:10],
            "movement_history": [
                {
                    "date": (row["moved_at"] or "—")[:10],
                    "from": row["from_loc"] or "—",
                    "to": row["to_loc"] or "—",
                    # Set when the row records a status change (REQ-11)
                    "status_change": (
                        f'{row["from_status"] or "—"} → {row["to_status"]}'
                        if row["to_status"] else None
                    ),
                }
                for row in history
            ],
        }
    finally:
        conn.close()


def get_compliance_report(owner_id):
    """Surplus/shortage across every one of the owner's buildings and item types."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT b.city AS building, it.name AS item_type, "
            "       p.target_qty AS target, p.present_qty AS on_hand, "
            "       p.available_qty AS available, "
            "       (p.present_qty - p.target_qty) AS variance "
            "FROM v_building_item_type_position p "
            "JOIN building b ON b.building_id = p.building_id "
            "JOIN business bs ON bs.business_id = b.business_id "
            "JOIN item_type it ON it.item_type_id = p.item_type_id "
            "WHERE bs.owner_id = ? "
            "ORDER BY b.city, it.name",
            (owner_id,),
        ).fetchall()
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


# ---------------------------------------------------------------------------
# Rooms and storage units (REQ-4, REQ-5)
# ---------------------------------------------------------------------------

class NotFoundOrNotOwned(Exception):
    """Raised when a write targets a record that doesn't exist or belongs to
    a different owner. The route treats both the same way, so a user can't
    use the error to find out which ids exist (NF-REQ-12)."""
    pass


def _building_owned_by(conn, building_id, owner_id):
    row = conn.execute(
        "SELECT 1 FROM building bl "
        "JOIN business bs ON bs.business_id = bl.business_id "
        "WHERE bl.building_id = ? AND bs.owner_id = ?",
        (building_id, owner_id),
    ).fetchone()
    return row is not None


def _room_owned_by(conn, room_id, owner_id):
    """Returns the room's building_id if the owner owns it, else None."""
    row = conn.execute(
        "SELECT r.building_id FROM room r "
        "JOIN building bl ON bl.building_id = r.building_id "
        "JOIN business bs ON bs.business_id = bl.business_id "
        "WHERE r.room_id = ? AND bs.owner_id = ?",
        (room_id, owner_id),
    ).fetchone()
    return row["building_id"] if row else None


def add_room(owner_id, building_id, name):
    """Create a room in one of the owner's buildings. Returns the new room_id."""
    conn = get_connection()
    try:
        if not _building_owned_by(conn, building_id, owner_id):
            raise NotFoundOrNotOwned()
        cur = conn.execute(
            "INSERT INTO room (building_id, location) VALUES (?, ?)",
            (building_id, name),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def add_storage(owner_id, room_id, storage_type):
    """Create a storage unit in one of the owner's rooms.

    Returns (storage_id, building_id) so the route knows which building page
    to send the user back to. storage_type is free text on purpose: the
    suggested types are only suggestions (NF-REQ-1).
    """
    conn = get_connection()
    try:
        building_id = _room_owned_by(conn, room_id, owner_id)
        if building_id is None:
            raise NotFoundOrNotOwned()
        cur = conn.execute(
            "INSERT INTO storage (room_id, storage_type) VALUES (?, ?)",
            (room_id, storage_type),
        )
        conn.commit()
        return cur.lastrowid, building_id
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Adding items (REQ-6, REQ-14)
# ---------------------------------------------------------------------------

MAX_ITEMS_PER_ADD = 100


def get_item_types():
    """All item types, for the Add Item form's dropdown."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT item_type_id, name FROM item_type ORDER BY name"
        ).fetchall()
        return [{"id": r["item_type_id"], "name": r["name"]} for r in rows]
    finally:
        conn.close()


def get_storage_choices(owner_id):
    """Every storage unit the owner has, labelled with its building and room,
    for the Add Item form's dropdown."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT s.storage_id, s.storage_type, r.location AS room, "
            "       bl.city, bl.street_address "
            "FROM storage s "
            "JOIN room r ON r.room_id = s.room_id "
            "JOIN building bl ON bl.building_id = r.building_id "
            "JOIN business bs ON bs.business_id = bl.business_id "
            "WHERE bs.owner_id = ? "
            "ORDER BY bl.building_id, r.room_id, s.storage_id",
            (owner_id,),
        ).fetchall()
        return [
            {
                "id": r["storage_id"],
                "building": f'{r["city"]} — {r["street_address"]}',
                "label": f'{r["room"]} / {r["storage_type"]}',
            }
            for r in rows
        ]
    finally:
        conn.close()


def add_items(owner_id, storage_id, item_type_id, quantity, name=""):
    """Add `quantity` items of one type to a storage unit in one action (REQ-14).

    Creates one item row per unit, each starting In Storage, plus one
    movement entry per item recording where it arrived (REQ-12). Everything
    is written in a single transaction: either all the items and their
    movement entries are saved, or none are.

    Names: a blank name becomes "<Type> #<n>", numbered on from the items of
    that type that already exist. A given name with quantity > 1 gets
    " #1", " #2", ... appended so the items can be told apart.

    Returns the list of new item_ids.
    """
    if not (1 <= quantity <= MAX_ITEMS_PER_ADD):
        raise ValueError(f"Quantity must be between 1 and {MAX_ITEMS_PER_ADD}.")

    conn = get_connection()
    try:
        owned = conn.execute(
            "SELECT 1 FROM storage s "
            "JOIN room r ON r.room_id = s.room_id "
            "JOIN building bl ON bl.building_id = r.building_id "
            "JOIN business bs ON bs.business_id = bl.business_id "
            "WHERE s.storage_id = ? AND bs.owner_id = ?",
            (storage_id, owner_id),
        ).fetchone()
        item_type = conn.execute(
            "SELECT name FROM item_type WHERE item_type_id = ?",
            (item_type_id,),
        ).fetchone()
        if owned is None or item_type is None:
            raise NotFoundOrNotOwned()

        name = (name or "").strip()
        if name:
            names = [name] if quantity == 1 else [f"{name} #{i}" for i in range(1, quantity + 1)]
        else:
            existing = conn.execute(
                "SELECT COUNT(*) FROM item WHERE item_type_id = ?", (item_type_id,)
            ).fetchone()[0]
            names = [f'{item_type["name"]} #{existing + i}' for i in range(1, quantity + 1)]

        new_ids = []
        for item_name in names:
            cur = conn.execute(
                "INSERT INTO item (item_type_id, storage_id, item_name, item_status) "
                "VALUES (?, ?, ?, 'In Storage')",
                (item_type_id, storage_id, item_name),
            )
            conn.execute(
                "INSERT INTO item_movement (item_id, from_storage_id, to_storage_id) "
                "VALUES (?, NULL, ?)",
                (cur.lastrowid, storage_id),
            )
            new_ids.append(cur.lastrowid)

        conn.commit()
        return new_ids
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Changing an item's status (REQ-11, REQ-12)
# ---------------------------------------------------------------------------

ITEM_STATUSES = ("In Storage", "In Use", "In Transit")


def update_item_status(owner_id, item_id, new_status, storage_id=None):
    """Change an item's status and log it in its movement history.

    Three cases, matching how schema v6 models status and location:

    - In Storage <-> In Use: the item stays where it is. The movement row
      records only the status change (from_status/to_status).
    - Anything -> In Transit: the item leaves its storage unit, so storage_id
      becomes NULL. The movement row records where it left from, which is
      also how its owner is still traced while it's travelling.
    - In Transit -> In Storage/In Use: the item has arrived somewhere, so a
      destination storage_id (one of the owner's) is required.

    The item update and the movement row are written in one transaction.
    Returns True if the status changed, False if it was already new_status.
    Raises ValueError for a bad status or a missing destination, and
    NotFoundOrNotOwned if the item or destination isn't the owner's.
    """
    if new_status not in ITEM_STATUSES:
        raise ValueError(f"Unknown status: {new_status}")

    conn = get_connection()
    try:
        item = conn.execute(
            "SELECT i.item_id, i.item_status, i.storage_id FROM item i "
            + _ITEM_OWNER_JOINS +
            "WHERE i.item_id = ? AND obs.owner_id = ?",
            (item_id, owner_id),
        ).fetchone()
        if item is None:
            raise NotFoundOrNotOwned()

        old_status = item["item_status"]
        old_storage = item["storage_id"]
        if new_status == old_status:
            return False

        if new_status == "In Transit":
            new_storage = None
        elif old_status == "In Transit":
            if not storage_id:
                raise ValueError("Choose where the item arrived.")
            owned = conn.execute(
                "SELECT 1 FROM storage s "
                "JOIN room r ON r.room_id = s.room_id "
                "JOIN building bl ON bl.building_id = r.building_id "
                "JOIN business bs ON bs.business_id = bl.business_id "
                "WHERE s.storage_id = ? AND bs.owner_id = ?",
                (storage_id, owner_id),
            ).fetchone()
            if owned is None:
                raise NotFoundOrNotOwned()
            new_storage = storage_id
        else:
            new_storage = old_storage

        conn.execute(
            "UPDATE item SET item_status = ?, storage_id = ? WHERE item_id = ?",
            (new_status, new_storage, item_id),
        )
        location_changed = new_storage != old_storage
        conn.execute(
            "INSERT INTO item_movement "
            "(item_id, from_storage_id, to_storage_id, from_status, to_status) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                item_id,
                old_storage if location_changed else None,
                new_storage if location_changed else None,
                old_status,
                new_status,
            ),
        )
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Businesses and buildings (the Dashboard's add/edit buttons)
# ---------------------------------------------------------------------------

def add_business(owner_id, name):
    """Create a business for the owner. Returns the new business_id."""
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO business (name, owner_id) VALUES (?, ?)",
            (name, owner_id),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def rename_business(owner_id, business_id, name):
    """Rename one of the owner's businesses."""
    conn = get_connection()
    try:
        cur = conn.execute(
            "UPDATE business SET name = ? WHERE business_id = ? AND owner_id = ?",
            (name, business_id, owner_id),
        )
        if cur.rowcount == 0:
            raise NotFoundOrNotOwned()
        conn.commit()
    finally:
        conn.close()


def add_building(owner_id, business_id, street_address, city, state):
    """Create a building under one of the owner's businesses.
    Returns the new building_id."""
    conn = get_connection()
    try:
        owned = conn.execute(
            "SELECT 1 FROM business WHERE business_id = ? AND owner_id = ?",
            (business_id, owner_id),
        ).fetchone()
        if owned is None:
            raise NotFoundOrNotOwned()
        cur = conn.execute(
            "INSERT INTO building (business_id, street_address, city, state) "
            "VALUES (?, ?, ?, ?)",
            (business_id, street_address, city, state),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Optimizer inputs (REQ-17, REQ-18) — read-only feed for redistribution.py
# ---------------------------------------------------------------------------

def get_optimizer_inputs(owner_id):
    """Everything the redistribution optimizer needs for one owner, as plain
    dicts so this layer stays free of any Optimizer imports.

    Returns a dict with:
      buildings   [{id, label}]   the owner's buildings, by building_id
      item_types  [{id, name, replacement_cost}]  replacement_cost None = c_k inf
      routes      [{from_id, to_id, distance_miles, fixed_dispatch_cost,
                    cost_per_unit_mile}]   only routes between the owner's buildings
      positions   [{building_id, item_type_id, supply, demand}]  rows with
                  shippable surplus (s_ik) or shortage (d_jk) > 0, read
                  straight from v_building_item_type_position

    A building's label is its city, plus the street address when the owner
    has more than one building in that city (e.g. the two Salina sites).
    Only owner_id's own data is read (NF-REQ-12).
    """
    conn = get_connection()
    try:
        buildings = conn.execute(
            "SELECT b.building_id, b.city, b.street_address "
            "FROM building b JOIN business bs ON bs.business_id = b.business_id "
            "WHERE bs.owner_id = ? ORDER BY b.building_id",
            (owner_id,),
        ).fetchall()
        owned = {b["building_id"] for b in buildings}

        city_counts = {}
        for b in buildings:
            city_counts[b["city"]] = city_counts.get(b["city"], 0) + 1

        def _label(b):
            city = b["city"] or f"Building {b['building_id']}"
            if city_counts.get(b["city"], 0) > 1 and b["street_address"]:
                return f"{city} ({b['street_address']})"
            return city

        item_types = conn.execute(
            "SELECT item_type_id, name, replacement_cost FROM item_type ORDER BY item_type_id"
        ).fetchall()

        routes = conn.execute(
            "SELECT from_building_id, to_building_id, distance_miles, "
            "       fixed_dispatch_cost, cost_per_unit_mile "
            "FROM building_route ORDER BY building_route_id"
        ).fetchall()

        positions = conn.execute(
            "SELECT p.building_id, p.item_type_id, "
            "       p.shippable_surplus_qty AS supply, p.shortage_qty AS demand "
            "FROM v_building_item_type_position p "
            "JOIN building b ON b.building_id = p.building_id "
            "JOIN business bs ON bs.business_id = b.business_id "
            "WHERE bs.owner_id = ? "
            "  AND (p.shippable_surplus_qty > 0 OR p.shortage_qty > 0) "
            "ORDER BY p.building_id, p.item_type_id",
            (owner_id,),
        ).fetchall()

        return {
            "buildings": [{"id": b["building_id"], "label": _label(b)} for b in buildings],
            "item_types": [
                {
                    "id": t["item_type_id"],
                    "name": t["name"],
                    "replacement_cost": None if t["replacement_cost"] is None
                                        else float(t["replacement_cost"]),
                }
                for t in item_types
            ],
            "routes": [
                {
                    "from_id": r["from_building_id"],
                    "to_id": r["to_building_id"],
                    "distance_miles": float(r["distance_miles"]),
                    "fixed_dispatch_cost": float(r["fixed_dispatch_cost"]),
                    "cost_per_unit_mile": float(r["cost_per_unit_mile"]),
                }
                for r in routes
                if r["from_building_id"] in owned and r["to_building_id"] in owned
            ],
            "positions": [
                {
                    "building_id": p["building_id"],
                    "item_type_id": p["item_type_id"],
                    "supply": int(p["supply"]),
                    "demand": int(p["demand"]),
                }
                for p in positions
            ],
        }
    finally:
        conn.close()
