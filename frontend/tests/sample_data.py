"""Canned API replies for page tests, in the shapes API_CONTRACT.md lists.

Loosely based on the seed data: Dale (owner_id 1) owns Prairie Roofing,
with a Hays building and a Salina building.
"""

OWNER = {"owner_id": 1, "first_name": "Dale", "last_name": "Prairie",
         "email": "dale@prairieroofing.example",
         "memberships": [{"business_id": 1, "role": "owner"}]}

EMPLOYEE = {"owner_id": 2, "first_name": "Jess", "last_name": "Crew",
            "email": "crew@prairieroofing.example",
            "memberships": [{"business_id": 1, "role": "employee"}]}

STORAGE_LOCKER = {"id": 1, "name": "Locker", "type": "Locker", "item_count": 3}
STORAGE_SHELF = {"id": 2, "name": "Shelf", "type": "Shelf", "item_count": 0}

HAYS = {
    "id": 1, "name": "Hays — 100 Main St", "address": "100 Main St, Hays, Kansas",
    "street_address": "100 Main St", "city": "Hays", "state": "Kansas",
    "room_count": 1, "storage_count": 2, "item_count": 3, "shortage_count": 1,
    "rooms": [{"id": 1, "name": "Tool Room", "storages": [STORAGE_LOCKER, STORAGE_SHELF]}],
}
SALINA = {
    "id": 2, "name": "Salina — 9 Elm Ave", "address": "9 Elm Ave, Salina, Kansas",
    "street_address": "9 Elm Ave", "city": "Salina", "state": "Kansas",
    "room_count": 0, "storage_count": 0, "item_count": 0, "shortage_count": 0,
    "rooms": [],
}


def dashboard(role="owner"):
    return [{"id": 1, "name": "Prairie Roofing", "role": role, "buildings": [HAYS, SALINA]}]


def building_report(role="owner"):
    b = {k: v for k, v in HAYS.items() if not k.endswith("_count")}
    b.update({
        "business_id": 1, "role": role,
        "compliance": [
            {"item_type_id": 1, "item_type": "Nail Gun", "target": 5, "on_hand": 3,
             "available": 3, "variance": -2},
            {"item_type_id": 2, "item_type": "Ladder", "target": 1, "on_hand": 1,
             "available": 1, "variance": 0},
        ],
    })
    return b


ITEM_TYPES = [
    {"item_type_id": 2, "name": "Ladder", "description": "24 ft", "replacement_cost": 300.0,
     "service_life_days": None},
    {"item_type_id": 1, "name": "Nail Gun", "description": None, "replacement_cost": 250.0,
     "service_life_days": 730},
]

ITEMS = [
    {"id": 1, "name": "Nail Gun #1", "type": "Nail Gun", "status": "In Storage",
     "building": "Hays", "room": "Tool Room", "storage": "Locker", "expired": True},
    {"id": 2, "name": "Nail Gun #2", "type": "Nail Gun", "status": "In Transit",
     "building": "In transit", "room": "—", "storage": "—", "expired": False},
]


def item_detail(item_id=1, status="In Storage", role="owner", expired=False):
    return {
        "id": item_id, "name": f"Nail Gun #{item_id}", "type": "Nail Gun", "item_type_id": 1,
        "status": status, "building": "Hays", "room": "Tool Room", "storage": "Locker",
        "storage_id": None if status == "In Transit" else 1, "date_added": "2024-01-02",
        "role": role, "expired": expired, "days_over": 30 if expired else None,
        "movement_history": [
            {"date": "2024-01-02", "from": "—", "to": "Hays / Tool Room / Locker",
             "status_change": None},
        ],
    }


STORAGE_CHOICES = [
    {"id": 1, "building": "Hays — 100 Main St", "label": "Tool Room / Locker"},
    {"id": 2, "building": "Hays — 100 Main St", "label": "Tool Room / Shelf"},
]

COMPLIANCE = [
    {"building_id": 1, "building": "Hays", "item_type_id": 1, "item_type": "Nail Gun",
     "target": 5, "on_hand": 3, "available": 3, "variance": -2},
    {"building_id": 2, "building": "Salina", "item_type_id": 1, "item_type": "Nail Gun",
     "target": 0, "on_hand": 4, "available": 4, "variance": 4},
]

EXPIRED = [
    {"id": 1, "name": "Nail Gun #1", "type": "Nail Gun", "status": "In Storage",
     "age_days": 760, "service_life_days": 730, "days_over": 30},
]


def storage_report(role="owner"):
    return {
        "id": 1, "type": "Locker", "role": role,
        "room": {"id": 1, "name": "Tool Room"},
        "building": {"id": 1, "name": "Hays — 100 Main St"},
        "items": [
            {"id": 1, "name": "Nail Gun #1", "type": "Nail Gun", "status": "In Storage",
             "expired": True},
            {"id": 3, "name": "Ladder #1", "type": "Ladder", "status": "In Use",
             "expired": False},
        ],
    }


MEMBERS = [
    {"business_member_id": 1, "business_id": 1, "owner_id": 1, "role": "owner",
     "first_name": "Dale", "last_name": "Prairie", "email": "dale@prairieroofing.example"},
    {"business_member_id": 2, "business_id": 1, "owner_id": 2, "role": "employee",
     "first_name": "Jess", "last_name": "Crew", "email": "crew@prairieroofing.example"},
]

ROUTES = [
    {"route_id": 1, "from_building_id": 1, "from_label": "Hays", "to_building_id": 2,
     "to_label": "Salina", "distance_miles": 98.0, "fixed_dispatch_cost": 75.0,
     "cost_per_unit_mile": 0.12, "handling_cost_per_unit": 11.76},
]

MOVEMENTS = [
    {"movement_id": 5, "date": "2026-11-02", "item_id": 2, "item_name": "Nail Gun #2",
     "item_type": "Nail Gun", "building": "Hays", "from": "Hays / Tool Room / Locker",
     "to": "—", "status_change": "In Storage → In Transit"},
    {"movement_id": 1, "date": "2024-01-02", "item_id": 1, "item_name": "Nail Gun #1",
     "item_type": "Nail Gun", "building": "Hays", "from": "—",
     "to": "Hays / Tool Room / Locker", "status_change": None},
]

PLAN = {
    "generated": True, "no_shortages": False, "optimal": True, "gap": 0.0,
    "total_cost": 98.52, "transfer_cost": 98.52, "acquisition_cost": 0.0,
    "greedy_cost": 120.0,
    "trips": [{"from": "Salina", "to": "Hays", "items": [{"qty": 2, "type": "Nail Gun"}],
               "dispatch_cost": 75.0, "handling_cost": 23.52}],
    "acquisitions": [],
    "shortage_costs": [{"building": "Hays", "type": "Nail Gun", "qty": 2,
                        "cost": 98.52, "cost_per_unit": 49.26}],
}


def default_returns():
    return {
        "login": OWNER,
        "register": {**OWNER, "memberships": []},
        "get_dashboard": dashboard(),
        "get_building_report": building_report(),
        "get_storage_report": storage_report(),
        "get_items": ITEMS,
        "get_item_detail": item_detail(),
        "get_compliance": COMPLIANCE,
        "get_expired_items": EXPIRED,
        "get_storage_choices": STORAGE_CHOICES,
        "get_item_types": ITEM_TYPES,
        "get_members": MEMBERS,
        "get_routes": ROUTES,
        "search_movements": MOVEMENTS,
        "export_movements_csv": "date,item_name\n2026-11-02,Nail Gun #2\n",
        "run_plan": PLAN,
        "add_items": [10],
        "change_item_status": True,
        "set_target": ({}, True),
        "add_building": {"building_id": 3, "business_id": 1, "street_address": "1 New Rd",
                         "city": "Hays", "state": "Kansas", "retired": None},
        "add_room": {"room_id": 4, "building_id": 1, "location": "Garage", "retired": None},
        "add_storage": {"storage_id": 5, "room_id": 1, "storage_type": "Bin", "retired": None},
    }
