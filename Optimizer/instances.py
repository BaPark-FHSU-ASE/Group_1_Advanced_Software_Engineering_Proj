"""
The two fully-specified, pre-solved instances.
Goal is to test against these data before linking to database


"""

from __future__ import annotations
from .models import Instance, ItemType, Route

# ---------------------------------------------------------------------------
# Instance A: three sites, two item types 
# ---------------------------------------------------------------------------

_A_ROUTE_DATA = {
    ("A", "C"): (4.6, 65.52, 0.05),
    ("A", "B"): (20.6, 84.72, 0.05),
    ("B", "C"): (20.9, 85.08, 0.05),
}


def instance_a() -> Instance:
    item_types = {
        "auger": ItemType("auger", replacement_cost=100_000.0),  # "large relative to transport"
        "skidsteer": ItemType("skidsteer", replacement_cost=100_000.0),
    }
    routes = {}
    for (u, v), (dist, fixed, rate) in _A_ROUTE_DATA.items():
        routes[(u, v)] = Route(u, v, dist, fixed, rate)
        routes[(v, u)] = Route(v, u, dist, fixed, rate)  # undirected

    return Instance(
        buildings=["A", "B", "C"],
        item_types=item_types,
        routes=routes,
        supply={("B", "auger"): 2, ("C", "auger"): 1, ("A", "skidsteer"): 3},
        demand={("A", "auger"): 2, ("C", "skidsteer"): 3},
    )


INSTANCE_A_NEAREST_SOURCE_COST = 217.71
INSTANCE_A_OPTIMAL_COST = 152.99

# ---------------------------------------------------------------------------
# Instance B: 5 sites
# ---------------------------------------------------------------------------

_B_SITES = ["SalN", "SalS", "Abil", "Hays", "GBend"]

_B_ROUTE_DATA = {
    ("SalN", "SalS"): (9.20, 71.04, 0.05),
    ("SalN", "Abil"): (24.60, 89.52, 0.05),
    ("SalN", "Hays"): (96.40, 175.68, 0.05),
    ("SalN", "GBend"): (88.70, 166.44, 0.05),
    ("SalS", "Abil"): (27.10, 92.52, 0.05),
    ("SalS", "Hays"): (94.00, 172.80, 0.05),
    ("SalS", "GBend"): (86.20, 163.44, 0.05),
    ("Abil", "Hays"): (118.50, 202.20, 0.05),
    ("Abil", "GBend"): (110.30, 192.36, 0.05),
    ("Hays", "GBend"): (58.90, 130.68, 0.05),
}

_B_REPLACEMENT_COSTS = {
    "nailgun": 340.00,
    "aircomp": 620.00,
    "ladder": 290.00,
    "hardhat": 38.00,
    "harness": 145.00,
    "shovel": 42.00,
}

# (building, type) -> s_ik
_B_SUPPLY = {
    ("SalN", "nailgun"): 3, ("SalN", "aircomp"): 1, ("SalN", "ladder"): 2,
    ("SalN", "hardhat"): 7, ("SalN", "harness"): 4, ("SalN", "shovel"): 5,
    ("SalS", "nailgun"): 1, ("SalS", "ladder"): 1, ("SalS", "shovel"): 2,
    ("Abil", "nailgun"): 2, ("Abil", "aircomp"): 1, ("Abil", "harness"): 2,
    ("Hays", "ladder"): 1,
}

# (building, type) -> d_jk
_B_DEMAND = {
    ("SalS", "aircomp"): 1, ("SalS", "harness"): 2,
    ("Abil", "hardhat"): 2,
    ("Hays", "nailgun"): 2, ("Hays", "aircomp"): 1, ("Hays", "hardhat"): 3, ("Hays", "shovel"): 2,
    ("GBend", "nailgun"): 1, ("GBend", "ladder"): 1, ("GBend", "hardhat"): 2, ("GBend", "harness"): 1,
}


def _instance_b(replacement_costs: dict[str, float | None]) -> Instance:
    item_types = {k: ItemType(k, replacement_costs[k]) for k in _B_REPLACEMENT_COSTS}
    routes = {}
    for (u, v), (dist, fixed, rate) in _B_ROUTE_DATA.items():
        routes[(u, v)] = Route(u, v, dist, fixed, rate)
        routes[(v, u)] = Route(v, u, dist, fixed, rate)

    return Instance(
        buildings=list(_B_SITES),
        item_types=item_types,
        routes=routes,
        supply=dict(_B_SUPPLY),
        demand=dict(_B_DEMAND),
    )


def instance_b() -> Instance:
    """The base instance: acquisition available at each type's replacement cost."""
    return _instance_b(dict(_B_REPLACEMENT_COSTS))


def instance_b_strict() -> Instance:
    """Assumption A4's strict variant: c_k = infinity for every type, so every
    shortage must be met by transfer. Doc's reference cost: $591.42, 4 routes."""
    return _instance_b({k: None for k in _B_REPLACEMENT_COSTS})


INSTANCE_B_OPTIMAL_COST = 575.44
INSTANCE_B_NEAREST_SOURCE_COST = 1072.19
INSTANCE_B_STRICT_COST = 591.42


def _print_instance(label: str, instance: Instance) -> None:
    print(f"{label}:")
    print(f"  buildings: {instance.buildings}")
    print(f"  item_types: {list(instance.item_types)}")
    print(f"  supply: {instance.supply}")
    print(f"  demand: {instance.demand}")


if __name__ == "__main__":
    # Run with: python -m Optimizer.instances
    # (a plain `python instances.py` breaks the relative import above)
    _print_instance("Instance A", instance_a())
    print()
    _print_instance("Instance B", instance_b())
