"""
Decision table for REQ-24 (buy a new item vs. transfer one), plus the
"no plan possible" case from extension 5a of Generate Redistribution Plan.

Every case is the same tiny setup: one source S, and one destination D that
is short 2 units of a single item type. Each column changes only the thing
being tested.

Conditions                        DT-1 DT-2 DT-3 DT-4 DT-5 DT-6 DT-7 DT-8 DT-9
C1 replacement cost recorded       Y    N    Y    Y    N    Y    N    Y    N
C2 shippable surplus reachable     N    N    all  all  all  part part N(*) N(*)
C3 transfer cheaper than buying    -    -    Y    N    N    Y    -    -    -
Action
A1 transfer                        .    .    X    .    X    X    .    .    .
A2 acquire                         X    .    .    X    .    X    .    X    .
A3 no plan (ValueError)            .    X    .    .    .    .    X    .    X

(*) In DT-8 and DT-9, S has surplus but there's no route between the two
    buildings (extension 4a), so S may as well not have any.
"""

import pytest

from Optimizer.branch_and_bound import branch_and_bound
from Optimizer.models import Instance, ItemType, Route

TOL = 0.005


def _instance(replacement_cost, surplus, *, fixed=72.0, miles=10.0, routed=True):
    """The two-building setup above. With the defaults, one trip costs
    $72 dispatch + $0.50 handling per unit."""
    routes = {}
    if routed:
        routes = {
            ("S", "D"): Route("S", "D", miles, fixed, 0.05),
            ("D", "S"): Route("D", "S", miles, fixed, 0.05),
        }
    supply = {("S", "k"): surplus} if surplus else {}
    return Instance(
        buildings=["S", "D"],
        item_types={"k": ItemType("k", replacement_cost)},
        routes=routes,
        supply=supply,
        demand={("D", "k"): 2},
    )


def _units_transferred(plan):
    return sum(sum(t.units_by_type.values()) for t in plan.trips)


def _units_acquired(plan):
    return sum(plan.acquisitions.values())


# (id, instance, units transferred, units bought, total cost)
FEASIBLE = [
    ("DT-1", _instance(100.0, 0), 0, 2, 200.00),
    ("DT-3", _instance(100.0, 5), 2, 0, 73.00),
    ("DT-4", _instance(30.0, 5), 0, 2, 60.00),
    ("DT-5", _instance(None, 5, fixed=5000.0), 2, 0, 5001.00),
    ("DT-6", _instance(100.0, 1), 1, 1, 172.50),
    ("DT-8", _instance(100.0, 5, routed=False), 0, 2, 200.00),
]


@pytest.mark.parametrize("case, instance, moved, bought, total", FEASIBLE)
def test_buy_versus_transfer(case, instance, moved, bought, total):
    plan, gap = branch_and_bound(instance)
    assert _units_transferred(plan) == moved, case
    assert _units_acquired(plan) == bought, case
    assert abs(plan.total_cost - total) < TOL, case
    assert gap == pytest.approx(0.0, abs=1e-9), case


@pytest.mark.parametrize(
    "case, instance",
    [
        ("DT-2", _instance(None, 0)),
        ("DT-7", _instance(None, 1)),
        ("DT-9", _instance(None, 5, routed=False)),
    ],
)
def test_no_plan_when_shortage_can_be_met_neither_way(case, instance):
    with pytest.raises(ValueError):
        branch_and_bound(instance)


# DT-9 does fail, which is right, but for the wrong reason. Without any
# routes or a way to buy, the LP ends up with zero variables, so linprog
# raises its own input error and the owner never sees our "infeasible"
# message. This is DEF-1. The xfail is strict, so as soon as
# that bug gets fixed this test will start failing to remind us to remove
# the marker.
@pytest.mark.xfail(
    strict=True,
    reason="DEF-1: no routes and no acquisition option leaves the LP with "
    "no variables, and linprog's input error escapes instead of our "
    "infeasibility message.",
)
def test_dt9_reports_infeasibility_not_a_solver_error():
    with pytest.raises(ValueError, match="infeasible"):
        branch_and_bound(_instance(None, 5, routed=False))


def test_tie_between_transfer_and_purchase_is_priced_correctly():
    """Boundary case. Transferring costs 72 + 2 x 0.50 = $73.00, and buying
    2 x 36.50 is also $73.00. Either one is optimal, so I only check the
    cost and don't care which option it picked."""
    plan, _gap = branch_and_bound(_instance(36.5, 5))
    assert abs(plan.total_cost - 73.00) < TOL
