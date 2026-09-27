"""
SolveResidual(Y): the exact integral optimum over a fixed set of permitted
routes. Once the route decisions are fixed, the problem separates into one
independent transportation problem per item type, each solved exactly by
min-cost flow (network.py). Every other solution procedure in this package
is built on top of this function.

Requirements traced: REQ-18 (the plan itself), REQ-24 (acquisition competes
against transfer inside the same network, and its cost is reported
separately).

Permitted, not forced
---------------------
`opened` is the set of routes the caller *allows* flow on, not a set of
routes that must be paid for. A permitted route that ends up carrying
nothing is not charged its dispatch cost and does not appear in
Plan.opened_routes.

What that does and does not buy: dropping the charge for unused routes makes
the returned figure the true cost of the plan actually produced. It does NOT
make that plan optimal over all subsets of `opened`. The flow solve minimises
handling plus acquisition only - it cannot see fixed dispatch charges - so it
will happily choose a cheap-handling route carrying a large fixed charge over
a slightly dearer route that is nearly free to open. Searching over subsets
is therefore still required, which is what enumerate_bruteforce and (later)
branch_and_bound do.

When branch_and_bound needs a "charge every permitted route" reading for node
bounding, that belongs here as a keyword flag on this function rather than as
a second, near-duplicate implementation.
"""

from __future__ import annotations

from collections.abc import Iterable

from .models import Instance, Plan, Trip
from .network import MinCostFlow

# Transfer arcs are bounded by the supply and demand arcs on either side of
# them, so they need no meaningful capacity of their own.
_UNCAPPED = 10**9


def solve_residual(
    instance: Instance, opened: Iterable[tuple[str, str]]
) -> Plan | None:
    """Cheapest plan using only the routes in `opened`.

    Returns None if the demand cannot be met on that route set - which
    happens when an item type has no replacement cost and the permitted
    routes cannot reach enough surplus to cover its shortage.
    """
    opened = frozenset(opened)

    units_by_route: dict[tuple[str, str], dict[str, int]] = {}
    acquisitions: dict[tuple[str, str], int] = {}
    handling_cost = 0.0
    acquisition_cost = 0.0

    building_index = {b: n for n, b in enumerate(instance.buildings)}
    n_buildings = len(instance.buildings)

    # Node layout, fixed for every item type:
    #   0            super-source
    #   1            super-sink
    #   2            acquisition (left unconnected when c_k is None)
    #   3 ..         origin side, one per building
    #   3+n ..       destination side, one per building
    SRC, SINK, ACQ = 0, 1, 2
    orig = lambda b: 3 + building_index[b]  # noqa: E731
    dest = lambda b: 3 + n_buildings + building_index[b]  # noqa: E731

    for k in instance.types_with_activity():
        need = sum(instance.demand.get((j, k), 0) for j in instance.buildings)
        if need == 0:
            continue

        item_type = instance.item_types[k]
        net = MinCostFlow(3 + 2 * n_buildings)

        for b in instance.buildings:
            s_bk = instance.supply.get((b, k), 0)
            if s_bk > 0:
                net.add_edge(SRC, orig(b), s_bk, 0.0)
            d_bk = instance.demand.get((b, k), 0)
            if d_bk > 0:
                net.add_edge(dest(b), SINK, d_bk, 0.0)

        if item_type.replacement_cost is not None:
            net.add_edge(SRC, ACQ, need, item_type.replacement_cost)
            for b in instance.buildings:
                d_bk = instance.demand.get((b, k), 0)
                if d_bk > 0:
                    net.add_edge(ACQ, dest(b), d_bk, 0.0)

        for (i, j) in opened:
            route = instance.routes[(i, j)]
            net.add_edge(orig(i), dest(j), _UNCAPPED, route.handling_cost_per_unit)

        try:
            net.min_cost_flow(SRC, SINK, need)
        except ValueError:
            # Not routable on this route set, and no acquisition arc to
            # absorb the remainder. Infeasible rather than expensive.
            return None

        for (i, j) in opened:
            moved = net.flow_on(orig(i), dest(j))
            if moved > 0:
                units_by_route.setdefault((i, j), {})[k] = moved
                handling_cost += moved * instance.routes[(i, j)].handling_cost_per_unit

        if item_type.replacement_cost is not None:
            for b in instance.buildings:
                bought = net.flow_on(ACQ, dest(b))
                if bought > 0:
                    acquisitions[(b, k)] = bought
                    acquisition_cost += bought * item_type.replacement_cost

    # A route is opened only if something actually rode on it.
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
