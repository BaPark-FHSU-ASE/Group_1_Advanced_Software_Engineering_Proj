"""
Data structures for the redistribution optimizer.

These mirror the notation in the project proposal.

Instance.supply[(i, k)]   == s_ik   (shippable surplus)
Instance.demand[(j, k)]   == d_jk   (shortage)
Route.fixed_dispatch_cost == f_ij
Route.cost_per_unit_mile, Route.distance_miles -> h_ij (handling_cost_per_unit)
ItemType.replacement_cost == c_k  (None means c_k = infinity: acquisition unavailable)


Not tied to the database - see hardcoded data in instances.py for the two pre-solved instances.
"""


from __future__ import annotations
from dataclasses import dataclass, field


# frozen because items are fixed once the instance is created, and we want to use them as dict keys.
@dataclass(frozen=True)
class ItemType:
    key: str
    replacement_cost: float | None  # c_k; None = unavailable (c_k = infinity)


# frozen because routes are fixed once the instance is created
@dataclass(frozen=True)
class Route:
    origin: str  # building key i
    dest: str  # building key j
    distance_miles: float
    fixed_dispatch_cost: float  # f_ij
    cost_per_unit_mile: float

    @property
    def handling_cost_per_unit(self) -> float:  # h_ij
        return self.distance_miles * self.cost_per_unit_mile


@dataclass
class Instance:
    """
    One redistribution problem: buildings, item types, routes, and each
    building/type's position (supply of shippable surplus, demand from
    shortage). Buildings and item types are referenced by string key
    everywhere else, so the branching/flow code never touches labels.
    """

    buildings: list[str]
    item_types: dict[str, ItemType]
    routes: dict[tuple[str, str], Route]  # keyed (origin, dest)
    supply: dict[tuple[str, str], int] = field(default_factory=dict)  # (building, type) -> s_ik
    demand: dict[tuple[str, str], int] = field(default_factory=dict)  # (building, type) -> d_jk

    def route_set(self) -> list[tuple[str, str]]:
        return list(self.routes.keys())

    def types_with_activity(self) -> list[str]:
        """Item types with nonzero supply or demand anywhere - the only ones
        SolveResidual needs to build a network for."""
        active = set()
        for (_, k), qty in self.supply.items():
            if qty > 0:
                active.add(k)
        for (_, k), qty in self.demand.items():
            if qty > 0:
                active.add(k)
        return sorted(active)


#A trip is a single dispatch from one building to another, carrying some number of units of each type. A plan is a collection of trips plus any acquisitions made instead of transferring.
@dataclass
class Trip:
    origin: str
    dest: str
    units_by_type: dict[str, int]  # item type key -> units carried
    dispatch_cost: float
    handling_cost: float

    @property
    def total_cost(self) -> float:
        return self.dispatch_cost + self.handling_cost

# a plan is a collection of trips plus any acquisitions made instead of transferring.
@dataclass
class Plan:
    """The realized output of a solve: which routes to open and what to
    carry, plus what to acquire instead of transferring."""

    trips: list[Trip]
    acquisitions: dict[tuple[str, str], int]  # (building, item type) -> units bought
    total_cost: float
    opened_routes: frozenset[tuple[str, str]]

    def acquisition_cost(self, instance: Instance) -> float:
        return sum(
            instance.item_types[k].replacement_cost * qty
            for (_, k), qty in self.acquisitions.items()
            if qty > 0
        )

    def describe(self, instance: Instance) -> str:
        lines = []
        for t in sorted(self.trips, key=lambda t: (t.origin, t.dest)):
            load = ", ".join(f"{u} {k}" for k, u in sorted(t.units_by_type.items()) if u > 0)
            lines.append(
                f"{t.origin} -> {t.dest}: {load}  "
                f"(dispatch ${t.dispatch_cost:.2f} + handling ${t.handling_cost:.2f} "
                f"= ${t.total_cost:.2f})"
            )
        for (j, k), qty in sorted(self.acquisitions.items()):
            if qty > 0:
                cost = instance.item_types[k].replacement_cost * qty
                lines.append(f"acquire at {j}: {qty} {k}  (${cost:.2f})")
        lines.append(f"total: ${self.total_cost:.2f}")
        return "\n".join(lines)
