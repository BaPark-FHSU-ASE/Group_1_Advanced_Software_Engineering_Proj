from app.db.connection import get_connection
from app.models.building_route import BuildingRoute


_VISIBLE_ROUTES = (
    "SELECT r.* FROM building_route r "
    "JOIN building f ON f.building_id = r.from_building_id "
    "JOIN building t ON t.building_id = r.to_building_id "
    "WHERE f.retired IS NULL AND t.retired IS NULL "
    "AND f.business_id IN (SELECT business_id FROM business_member WHERE owner_id = ?) "
    "AND t.business_id IN (SELECT business_id FROM business_member WHERE owner_id = ?)"
)


def get_visible(user_id):
    """Every route the person can see, oldest first."""
    conn = get_connection()
    try:
        rows = conn.execute(
            _VISIBLE_ROUTES + " ORDER BY r.building_route_id", (user_id, user_id)
        ).fetchall()
    finally:
        conn.close()

    return [BuildingRoute.from_row(row) for row in rows]


def get_visible_by_id(user_id, route_id):
    conn = get_connection()
    try:
        row = conn.execute(
            _VISIBLE_ROUTES + " AND r.building_route_id = ?", (user_id, user_id, route_id)
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        return None

    return BuildingRoute.from_row(row)


def get_by_pair(from_building_id, to_building_id):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM building_route WHERE from_building_id = ? AND to_building_id = ?",
            (from_building_id, to_building_id),
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        return None

    return BuildingRoute.from_row(row)


def building_labels(user_id):
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT b.building_id, b.city, b.street_address FROM building b "
            "WHERE b.retired IS NULL AND b.business_id IN "
            "(SELECT business_id FROM business_member WHERE owner_id = ?) "
            "ORDER BY b.building_id",
            (user_id,),
        ).fetchall()
    finally:
        conn.close()

    in_city = {}
    for row in rows:
        in_city[row["city"]] = in_city.get(row["city"], 0) + 1

    labels = {}
    for row in rows:
        city = row["city"] or f"Building {row['building_id']}"
        if in_city[row["city"]] > 1 and row["street_address"]:
            labels[row["building_id"]] = f"{city} ({row['street_address']})"
        else:
            labels[row["building_id"]] = city
    return labels


def create(from_building_id, to_building_id, distance_miles, fixed_dispatch_cost, cost_per_unit_mile):
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO building_route (from_building_id, to_building_id, distance_miles, "
            "fixed_dispatch_cost, cost_per_unit_mile) VALUES (?, ?, ?, ?, ?)",
            (from_building_id, to_building_id, distance_miles, fixed_dispatch_cost, cost_per_unit_mile),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM building_route WHERE building_route_id = ?", (cursor.lastrowid,)
        ).fetchone()
    finally:
        conn.close()

    return BuildingRoute.from_row(row)


def update(route_id, distance_miles, fixed_dispatch_cost, cost_per_unit_mile):
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE building_route SET distance_miles = ?, fixed_dispatch_cost = ?, "
            "cost_per_unit_mile = ? WHERE building_route_id = ?",
            (distance_miles, fixed_dispatch_cost, cost_per_unit_mile, route_id),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM building_route WHERE building_route_id = ?", (route_id,)
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        return None

    return BuildingRoute.from_row(row)


def delete(route_id):
    conn = get_connection()
    try:
        cursor = conn.execute("DELETE FROM building_route WHERE building_route_id = ?", (route_id,))
        conn.commit()
    finally:
        conn.close()

    return cursor.rowcount > 0