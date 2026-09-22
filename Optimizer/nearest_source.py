"""
NearestSourceFirst: the REQ-20 baseline, reported alongside the optimum so
the owner can see what the optimisation is worth.

Deliberately myopic. Each shortage is filled in turn from whichever source
is nearest and still holds stock, with no regard for whether a route is
already being used for something else. That is the whole point: it is what
an owner would do by hand, and the gap between it and the optimum is the
value the decision-support layer adds.

Determinism. "Nearest" means the lowest handling_cost_per_unit on the
directed route from the source to the shorting building. Ties break on
fixed_dispatch_cost, then on the origin key, so the same instance always
produces the same plan.

Directed routes. Dispatch is charged once per distinct route actually used,
not once per transfer - but (i, j) and (j, i) are different routes and each
carries its own charge. In instance A this is exactly what makes the
baseline $217.71: C->A and A->C are both opened, and both are paid for.
"""

from __future__ import annotations

from .models import Instance, Plan, Trip


def nearest_source_first(instance: Instance) -> Plan | None:
    """Greedy nearest-source plan.

    Returns None if some shortage can be met neither by transfer nor by
    acquisition - that is, an item type with no replacement cost whose
    demand no reachable source can cover.
    """
    remaining_supply = dict(instance.supply)

    units_by_route: dict[tuple[str, str], dict[str, int]] = {}
    acquisitions: dict[tuple[str, str], int] = {}
    handling_cost = 0.0
    acquisition_cost = 0.0

    for j in instance.buildings:
        for k in instance.types_with_activity():
            remaining = instance.demand.get((j, k), 0)
            if remaining <= 0:
                continue

            while remaining > 0:
                candidates = [
                    i
                    for i in instance.buildings
                    if remaining_supply.get((i, k), 0) > 0
                    and (i, j) in instance.routes
                ]
                if not candidates:
                    break

                i_star = min(
                    candidates,
                    key=lambda i: (
                        instance.routes[(i, j)].handling_cost_per_unit,
                        instance.routes[(i, j)].fixed_dispatch_cost,
                        i,
                    ),
                )
                route = instance.routes[(i_star, j)]
                take = min(remaining, remaining_supply[(i_star, k)])

                remaining_supply[(i_star, k)] -= take
                remaining -= take
                carried = units_by_route.setdefault((i_star, j), {})
                carried[k] = carried.get(k, 0) + take
                handling_cost += take * route.handling_cost_per_unit

            if remaining > 0:
                # Nothing reachable left. Buy it, or admit defeat.
                replacement_cost = instance.item_types[k].replacement_cost
                if replacement_cost is None:
                    return None
                acquisitions[(j, k)] = acquisitions.get((j, k), 0) + remaining
                acquisition_cost += remaining * replacement_cost

    opened_routes = frozenset(units_by_route)
    dispatch_cost = sum(
        instance.routes[r].fixed_dispatch_cost for r in opened_routes
    )

    trips = [
        Trip(
            origin=i,
            dest=j,
            units_by_type=units,
            dispatch_cost=instance.routes[(i, j)].fixed_dispatch_cost,
            handling_cost=sum(
                n * instance.routes[(i, j)].handling_cost_per_unit
                for n in units.values()
            ),
        )
        for (i, j), units in units_by_route.items()
    ]

    return Plan(
        trips=trips,
        acquisitions=acquisitions,
        total_cost=dispatch_cost + handling_cost + acquisition_cost,
        opened_routes=opened_routes,
    )
