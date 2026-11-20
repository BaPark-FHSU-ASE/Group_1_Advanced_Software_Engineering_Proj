"""
Production solver. Builds the Section 10b model and gives it to SciPy's
MILP solver (HiGHS), which does the branch and bound for us.

We switched to this in V2 because our own branch_and_bound couldn't hit
NF-REQ-7. It re-solves an LP from scratch at every node, and the worst
benchmark instance took ~4,200 of them (17.6 s, limit is 5 s). HiGHS does
all 20 benchmark instances in under 0.3 s. This is the R-1 backup plan
from the risk register.

HiGHS only picks which routes to open. solve_residual still works out the
trips on those routes, so all the costs on the plan come from the same
code as before, and the quantities always come out as whole numbers.

branch_and_bound.py is still around as a second solver for the tests.

Returns (plan, gap) just like branch_and_bound. gap = 0 means optimal,
gap > 0 means we ran out of time and it's the best plan found so far.

Requirements traced: REQ-18, REQ-24, NF-REQ-7, NF-REQ-8.
"""

from __future__ import annotations

import time

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import csr_matrix

from .feasibility import check_fillable
from .models import Instance, Plan
from .nearest_source import nearest_source_first
from .residual import solve_residual

RouteKey = tuple[str, str]

# Leave a little of the deadline for building the model and running
# solve_residual afterwards. Both take a few ms.
_RESERVE_SECONDS = 0.25

# status codes milp returns
_OPTIMAL, _LIMIT_REACHED, _INFEASIBLE = 0, 1, 2


def _build_model(instance: Instance):
    """Build the model as sparse matrices. Returns (c, constraints,
    integrality, bounds, y_index); y_index maps each route to its column."""
    types = instance.types_with_activity()

    x_cols = [
        (i, j, k)
        for (i, j) in instance.route_set()
        for k in types
        if instance.supply.get((i, k), 0) > 0 and instance.demand.get((j, k), 0) > 0
    ]
    # Only routes that could carry something get a y variable. If the
    # origin has nothing the destination needs, the route would never be
    # opened anyway (same trick as in 10d).
    useful_routes = sorted({(i, j) for i, j, _ in x_cols})
    a_cols = [
        (j, k)
        for (j, k), need in sorted(instance.demand.items())
        if need > 0 and instance.item_types[k].replacement_cost is not None
    ]

    n_x, n_y = len(x_cols), len(useful_routes)
    x_index = {key: n for n, key in enumerate(x_cols)}
    y_index = {r: n_x + n for n, r in enumerate(useful_routes)}
    a_index = {key: n_x + n_y + n for n, key in enumerate(a_cols)}
    n_vars = n_x + n_y + len(a_cols)

    # objective = dispatch + handling + buying new
    c = np.zeros(n_vars)
    for (i, j, k), col in x_index.items():
        c[col] = instance.routes[(i, j)].handling_cost_per_unit
    for r, col in y_index.items():
        c[col] = instance.routes[r].fixed_dispatch_cost
    for (j, k), col in a_index.items():
        c[col] = instance.item_types[k].replacement_cost

    # group x columns by origin and by destination up front so we don't
    # have to search for them for every row
    into: dict[tuple[str, str], list[int]] = {}
    out_of: dict[tuple[str, str], list[int]] = {}
    for (i, j, k), col in x_index.items():
        into.setdefault((j, k), []).append(col)
        out_of.setdefault((i, k), []).append(col)

    rows, cols, vals, lower, upper = [], [], [], [], []

    def add_row(entries, lo, hi):
        r = len(lower)
        for col, v in entries:
            rows.append(r)
            cols.append(col)
            vals.append(v)
        lower.append(lo)
        upper.append(hi)

    # C1: can't ship more than the shippable surplus
    for (i, k), surplus in sorted(instance.supply.items()):
        if surplus > 0 and (i, k) in out_of:
            add_row([(col, 1.0) for col in out_of[(i, k)]], -np.inf, surplus)

    # C2: transfers in + purchases = shortage
    for (j, k), need in sorted(instance.demand.items()):
        if need <= 0:
            continue
        entries = [(col, 1.0) for col in into.get((j, k), [])]
        if (j, k) in a_index:
            entries.append((a_index[(j, k)], 1.0))
        add_row(entries, need, need)

    # C3: no flow on a route unless it's open
    for (i, j, k), col in x_index.items():
        cap = min(instance.supply[(i, k)], instance.demand[(j, k)])
        add_row([(col, 1.0), (y_index[(i, j)], -float(cap))], -np.inf, 0.0)

    a_matrix = csr_matrix((vals, (rows, cols)), shape=(len(lower), n_vars))
    constraints = LinearConstraint(a_matrix, np.array(lower), np.array(upper))

    # only y has to be 0/1. x and a can be continuous here because
    # solve_residual redoes the flows in whole numbers afterwards
    integrality = np.zeros(n_vars)
    integrality[n_x:n_x + n_y] = 1

    lo_bounds = np.zeros(n_vars)
    hi_bounds = np.full(n_vars, np.inf)
    hi_bounds[n_x:n_x + n_y] = 1.0

    return c, constraints, integrality, Bounds(lo_bounds, hi_bounds), y_index


def solve_milp(instance: Instance, deadline_seconds: float = 30.0) -> tuple[Plan, float]:
    """Returns (plan, gap), same as branch_and_bound.

    Raises UnfillableShortageError (a ValueError) if a shortage can't be
    filled at all, and ValueError if there's no plan for some other reason
    or nothing was found before the deadline.
    """
    start = time.monotonic()
    check_fillable(instance)

    if not any(qty > 0 for qty in instance.demand.values()):
        # nothing is short, so the best plan is doing nothing
        return Plan(trips=[], acquisitions={}, total_cost=0.0, opened_routes=frozenset()), 0.0

    # greedy plan as a backup in case HiGHS runs out of time before it
    # finds anything (really only happens with a tiny deadline). It can
    # return None, that's fine.
    greedy = nearest_source_first(instance)

    c, constraints, integrality, bounds, y_index = _build_model(instance)
    time_left = deadline_seconds - (time.monotonic() - start) - _RESERVE_SECONDS

    best, lower_bound = greedy, None
    if time_left > 0:
        result = milp(
            c,
            constraints=constraints,
            integrality=integrality,
            bounds=bounds,
            options={"time_limit": time_left},
        )
        if result.status == _INFEASIBLE:
            raise ValueError("instance is infeasible: no combination of transfers and purchases meets every shortage")

        if result.x is not None:
            opened = {r for r, col in y_index.items() if result.x[col] > 0.5}
            plan = solve_residual(instance, opened)
            # shouldn't ever be None since HiGHS already found a plan on
            # these routes, but if it is, just keep the greedy one
            if plan is not None and (best is None or plan.total_cost < best.total_cost):
                best = plan
        if result.status == _OPTIMAL and best is not None:
            return best, 0.0
        if result.status == _LIMIT_REACHED:
            lower_bound = result.mip_dual_bound

    if best is None:
        raise ValueError("no feasible plan found before the deadline elapsed")

    # Ran out of time. Gap is worked out the same way as branch_and_bound:
    # (plan - best possible) / plan. If HiGHS didn't give us a bound we
    # can't say how close we are, so call it 100%.
    if lower_bound is None or not np.isfinite(lower_bound) or best.total_cost <= 0:
        return best, 1.0
    return best, max(0.0, (best.total_cost - lower_bound) / best.total_cost)
