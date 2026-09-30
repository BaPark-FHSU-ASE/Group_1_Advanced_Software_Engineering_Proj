"""
BranchAndBound: the production method. Branches only on route-opening
decisions y_ij; once y is fixed, solve_residual finds the exact integral
optimum for the rest, so the LP relaxation only needs to bound the y
variables to be integral for a node to be accepted as a candidate
incumbent.

Implementation note: LPBound(O, F) is delegated to scipy.optimize.linprog
(HiGHS) rather than a hand-rolled simplex. The project's own reference
solutions were verified the same way (HiGHS via scipy.optimize.milp), so
this is consistent with how the regression targets were produced. The
search itself - which nodes get explored, how they're pruned, what gets
branched on, when to stop - is this module's own logic; linprog only
answers "what does the LP relaxation of this one node cost."
"""

from __future__ import annotations

import heapq
import itertools
import math
import time

import numpy as np
from scipy.optimize import linprog

from .models import Instance, Plan
from .nearest_source import nearest_source_first
from .residual import solve_residual

RouteKey = tuple[str, str]


def _lp_bound(
    instance: Instance, forced_open: frozenset[RouteKey], forced_closed: frozenset[RouteKey]
) -> tuple[float, dict[RouteKey, float]] | None:
    routes = instance.route_set()
    active_types = instance.types_with_activity()

    x_index: dict[tuple[str, str, str], int] = {}
    for (i, j) in routes:
        for k in active_types:
            s_ik = instance.supply.get((i, k), 0)
            d_jk = instance.demand.get((j, k), 0)
            if s_ik > 0 and d_jk > 0:
                x_index[(i, j, k)] = len(x_index)

    n_x = len(x_index)
    y_index = {r: n_x + idx for idx, r in enumerate(routes)}
    n_y = len(routes)

    a_index: dict[tuple[str, str], int] = {}
    for j in instance.buildings:
        for k in active_types:
            d_jk = instance.demand.get((j, k), 0)
            item_type = instance.item_types[k]
            if d_jk > 0 and item_type.replacement_cost is not None:
                a_index[(j, k)] = n_x + n_y + len(a_index)

    n_vars = n_x + n_y + len(a_index)
    c = np.zeros(n_vars)
    for (i, j, k), idx in x_index.items():
        c[idx] = instance.routes[(i, j)].handling_cost_per_unit
    for r, idx in y_index.items():
        c[idx] = instance.routes[r].fixed_dispatch_cost
    for (j, k), idx in a_index.items():
        c[idx] = instance.item_types[k].replacement_cost

    bounds = [(0.0, None)] * n_x
    for r in routes:
        if r in forced_open:
            bounds.append((1.0, 1.0))
        elif r in forced_closed:
            bounds.append((0.0, 0.0))
        else:
            bounds.append((0.0, 1.0))
    bounds += [(0.0, None)] * len(a_index)

    a_eq_rows, b_eq = [], []
    for j in instance.buildings:
        for k in active_types:
            d_jk = instance.demand.get((j, k), 0)
            if d_jk <= 0:
                continue
            row = np.zeros(n_vars)
            for i in instance.buildings:
                idx = x_index.get((i, j, k))
                if idx is not None:
                    row[idx] = 1.0
            a_idx = a_index.get((j, k))
            if a_idx is not None:
                row[a_idx] = 1.0
            a_eq_rows.append(row)
            b_eq.append(d_jk)

    a_ub_rows, b_ub = [], []
    for i in instance.buildings:  # supply capacity
        for k in active_types:
            s_ik = instance.supply.get((i, k), 0)
            if s_ik <= 0:
                continue
            row = np.zeros(n_vars)
            any_var = False
            for (oi, j) in routes:
                if oi != i:
                    continue
                idx = x_index.get((i, j, k))
                if idx is not None:
                    row[idx] = 1.0
                    any_var = True
            if any_var:
                a_ub_rows.append(row)
                b_ub.append(s_ik)

    for (i, j, k), idx in x_index.items():  # flow only on opened routes
        s_ik = instance.supply[(i, k)]
        d_jk = instance.demand[(j, k)]
        row = np.zeros(n_vars)
        row[idx] = 1.0
        row[y_index[(i, j)]] = -min(s_ik, d_jk)
        a_ub_rows.append(row)
        b_ub.append(0.0)

    result = linprog(
        c,
        A_ub=np.array(a_ub_rows) if a_ub_rows else None,
        b_ub=np.array(b_ub) if b_ub else None,
        A_eq=np.array(a_eq_rows) if a_eq_rows else None,
        b_eq=np.array(b_eq) if b_eq else None,
        bounds=bounds,
        method="highs",
    )
    if not result.success:
        return None
    y_values = {r: float(result.x[idx]) for r, idx in y_index.items()}
    return float(result.fun), y_values


def branch_and_bound(instance: Instance, deadline_seconds: float = 30.0) -> tuple[Plan, float]:
    """Returns (plan, gap). gap == 0.0 certifies optimality; a positive gap
    bounds how far the returned plan can be from optimal, which is what
    NF-REQ-8 requires be reported rather than presented as an optimal
    result when the deadline elapses first."""
    start = time.monotonic()

    # The greedy baseline is only a seed, and it is allowed to fail. It
    # consumes supply myopically in building order, so it can hand a source
    # to one shortage that a later shortage needed and return None on an
    # instance that is in fact feasible. Start with no incumbent rather
    # than treating that as infeasibility: pruning simply does not engage
    # until the first integral node is accepted.
    incumbent = nearest_source_first(instance)
    best_plan = incumbent
    z_inc = math.inf if incumbent is None else incumbent.total_cost

    root = _lp_bound(instance, frozenset(), frozenset())
    if root is None:
        raise ValueError("instance is infeasible even under full LP relaxation")

    counter = itertools.count()
    empty: frozenset[RouteKey] = frozenset()
    heap = [(root[0], next(counter), empty, empty, root[1])]

    while heap and time.monotonic() - start < deadline_seconds:
        zhat, _, opened_forced, closed_forced, yhat = heapq.heappop(heap)
        if zhat >= z_inc - 1e-9:
            continue

        free_fractional = [
            (r, v)
            for r, v in yhat.items()
            if r not in opened_forced and r not in closed_forced and 1e-6 < v < 1 - 1e-6
        ]
        if not free_fractional:
            opened = opened_forced | {
                r
                for r, v in yhat.items()
                if r not in opened_forced and r not in closed_forced and v > 0.5
            }
            plan = solve_residual(instance, opened)
            if plan is None:
                # This route set cannot meet demand - an item type with no
                # replacement cost whose shortage it cannot reach. The LP
                # bound was optimistic about it; it is not a candidate.
                continue
            if plan.total_cost < z_inc:
                z_inc = plan.total_cost
                best_plan = plan
            continue

        branch_route, _ = max(free_fractional, key=lambda rv: min(rv[1], 1 - rv[1]))
        for new_open, new_closed in (
            (opened_forced | {branch_route}, closed_forced),
            (opened_forced, closed_forced | {branch_route}),
        ):
            child = _lp_bound(instance, new_open, new_closed)
            if child is not None:
                heapq.heappush(heap, (child[0], next(counter), new_open, new_closed, child[1]))

    if best_plan is None:
        # Section 11d, fail rather than return a wrong answer: no integral
        # node was accepted and the greedy seed failed too, so there is no
        # plan to report - and certainly not a zero-cost one.
        raise ValueError("no feasible plan found before the deadline elapsed")

    remaining_bound = min((entry[0] for entry in heap), default=z_inc)
    gap = 0.0 if z_inc <= 0 else max(0.0, (z_inc - remaining_bound) / z_inc)
    return best_plan, gap
