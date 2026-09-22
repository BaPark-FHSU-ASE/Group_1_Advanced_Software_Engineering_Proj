"""
Exhaustive enumeration over route subsets: the verification oracle.

This is a TEST ORACLE, NOT A PRODUCTION PATH. It is exponential in the worst
case. Its job is to certify the other procedures on instances small enough to
settle by brute force, so that a disagreement between it and the production
solver is a bug report rather than a matter of opinion.

Two reductions make the reference instances tractable:

1. Useful-route filter. A directed route (i, j) can only ever carry
   something if i holds surplus of some type j is short of. Every other
   route is dead weight in the search. On instance B this cuts 20 routes to
   10, and 2^20 subsets to 2^10.

2. Dispatch-cost dominance. Seed the incumbent by permitting every useful
   route, then skip any subset whose fixed dispatch costs alone already
   match or exceed the incumbent, without solving its flow at all.

   This is sound despite solve_residual charging only the routes it actually
   uses. For any subset S, the plan it yields opens some O subset of S, and
   that same flow is feasible on O, so solve_residual(O) is no dearer. Since
   O's dispatch sum is at most that plan's total cost, O itself is never
   pruned. Every attainable cost is therefore still reached at some
   un-pruned subset.

Together these take instance B from roughly a million flow solves to a few
hundred.
"""

from __future__ import annotations

from itertools import combinations

from .models import Instance, Plan
from .residual import solve_residual


def useful_routes(instance: Instance) -> list[tuple[str, str]]:
    """Routes that could carry something: origin has surplus of a type the
    destination is short of. Public because the tests assert that this
    filter never discards a route from a known optimal solution."""
    active = instance.types_with_activity()
    return [
        (i, j)
        for (i, j) in instance.route_set()
        if any(
            instance.supply.get((i, k), 0) > 0 and instance.demand.get((j, k), 0) > 0
            for k in active
        )
    ]


def enumerate_bruteforce(instance: Instance) -> Plan | None:
    """Cheapest plan over every subset of the useful routes.

    Returns None if no subset can meet demand.
    """
    candidates = useful_routes(instance)

    # Permitting every useful route is equivalent to permitting every route -
    # the ones filtered out can carry nothing - so if this is infeasible, so
    # is every subset of it.
    best = solve_residual(instance, candidates)
    if best is None:
        return None

    for size in range(len(candidates) + 1):
        for subset in combinations(candidates, size):
            dispatch_floor = sum(
                instance.routes[r].fixed_dispatch_cost for r in subset
            )
            if dispatch_floor >= best.total_cost - 1e-9:
                continue
            plan = solve_residual(instance, subset)
            if plan is not None and plan.total_cost < best.total_cost:
                best = plan

    return best
