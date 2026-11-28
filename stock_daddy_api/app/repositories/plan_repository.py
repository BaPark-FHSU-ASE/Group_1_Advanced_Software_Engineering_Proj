"""
All the SQL for redistribution plans (REQ-18 to REQ-22, REQ-27).

Moved here from the frontend's db.get_optimizer_inputs when the frontend
switched over to the API. Same idea as before: hand the optimizer plain
dicts, so nothing in this file knows about Optimizer classes.

A plan covers every business the user owns (role 'owner' in
business_member). Retired businesses and buildings are left out, and the
stocking-position view already skips retired items, storage and rooms, and
only counts In Storage items as shippable.
"""

import json

from app.db.connection import get_connection


def owned_business_ids(user_id):
    """Active businesses where user_id has the owner role, lowest id first."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT b.business_id FROM business b "
            "JOIN business_member m ON m.business_id = b.business_id "
            "WHERE m.owner_id = ? AND m.role = 'owner' AND b.retired IS NULL "
            "ORDER BY b.business_id",
            (user_id,),
        ).fetchall()
    finally:
        conn.close()
    return [row["business_id"] for row in rows]


def get_optimizer_inputs(business_ids):
    """Everything the optimizer needs for these businesses.

    Returns {buildings, item_types, routes, positions}, same shape the old
    frontend adapter used:
      buildings   [{id, label}]
      item_types  [{id, name, replacement_cost}]   None = can't be bought
      routes      [{from_id, to_id, distance_miles, fixed_dispatch_cost,
                    cost_per_unit_mile}]   only between these buildings
      positions   [{building_id, item_type_id, supply, demand}]
    """
    if not business_ids:
        return {"buildings": [], "item_types": [], "routes": [], "positions": []}

    marks = ",".join("?" * len(business_ids))
    conn = get_connection()
    try:
        buildings = conn.execute(
            "SELECT building_id, city, street_address FROM building "
            f"WHERE business_id IN ({marks}) AND retired IS NULL "
            "ORDER BY building_id",
            business_ids,
        ).fetchall()
        active = {b["building_id"] for b in buildings}

        item_types = conn.execute(
            "SELECT item_type_id, name, replacement_cost FROM item_type "
            "ORDER BY item_type_id"
        ).fetchall()

        routes = conn.execute(
            "SELECT from_building_id, to_building_id, distance_miles, "
            "       fixed_dispatch_cost, cost_per_unit_mile "
            "FROM building_route ORDER BY building_route_id"
        ).fetchall()

        positions = conn.execute(
            "SELECT building_id, item_type_id, "
            "       shippable_surplus_qty AS supply, shortage_qty AS demand "
            "FROM v_building_item_type_position "
            "WHERE shippable_surplus_qty > 0 OR shortage_qty > 0 "
            "ORDER BY building_id, item_type_id"
        ).fetchall()
    finally:
        conn.close()

    return {
        "buildings": [{"id": b["building_id"], "label": _label(b, buildings)}
                      for b in buildings],
        "item_types": [
            {
                "id": t["item_type_id"],
                "name": t["name"],
                "replacement_cost": None if t["replacement_cost"] is None
                                    else float(t["replacement_cost"]),
            }
            for t in item_types
        ],
        # routes to or from a retired (or someone else's) building are dropped
        "routes": [
            {
                "from_id": r["from_building_id"],
                "to_id": r["to_building_id"],
                "distance_miles": float(r["distance_miles"]),
                "fixed_dispatch_cost": float(r["fixed_dispatch_cost"]),
                "cost_per_unit_mile": float(r["cost_per_unit_mile"]),
            }
            for r in routes
            if r["from_building_id"] in active and r["to_building_id"] in active
        ],
        "positions": [
            {
                "building_id": p["building_id"],
                "item_type_id": p["item_type_id"],
                "supply": int(p["supply"]),
                "demand": int(p["demand"]),
            }
            for p in positions
            if p["building_id"] in active
        ],
    }


def _label(building, all_buildings):
    # City name, plus the street when two buildings share a city
    # (e.g. the two Salina sites in the seed data).
    city = building["city"] or f"Building {building['building_id']}"
    same_city = sum(1 for b in all_buildings if b["city"] == building["city"])
    if same_city > 1 and building["street_address"]:
        return f"{city} ({building['street_address']})"
    return city


def available_items(building_id, item_type_id):
    """Items that could go on a truck from this building: In Storage, not
    retired, in storage that isn't retired. Oldest id first so the same
    plan always picks the same items. Returns [(item_id, name)]."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT i.item_id, i.item_name FROM item i "
            "JOIN storage s ON s.storage_id = i.storage_id "
            "JOIN room r ON r.room_id = s.room_id "
            "WHERE r.building_id = ? AND i.item_type_id = ? "
            "  AND i.item_status = 'In Storage' "
            "  AND i.retired IS NULL AND s.retired IS NULL AND r.retired IS NULL "
            "ORDER BY i.item_id",
            (building_id, item_type_id),
        ).fetchall()
    finally:
        conn.close()
    return [(row["item_id"], row["item_name"] or f"Item #{row['item_id']}")
            for row in rows]


def save_plan_run(business_id, run_by, method, total_cost, baseline_cost, gap, plan):
    """Save one run to plan_run (REQ-27). Returns the new plan_run_id."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO plan_run (business_id, run_by, method, total_cost, "
            "                      baseline_cost, gap, plan_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (business_id, run_by, method, round(total_cost, 2),
             round(baseline_cost, 2), round(gap, 4), json.dumps(plan)),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()
