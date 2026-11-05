"""
Tests for the up-front "can every shortage actually be filled?" check
(DEF-1).

Before this check existed, a shortage with no route to it and no way to buy
the item left the LP with nothing to solve, and the owner got SciPy's
"Invalid input for linprog" instead of an explanation. Now branch_and_bound
looks for that case before it calls SciPy at all.
"""

import pytest

import Optimizer.branch_and_bound as bb
from Optimizer.branch_and_bound import branch_and_bound
from Optimizer.feasibility import UnfillableShortageError, find_unfillable_shortages
from Optimizer.instances import instance_a, instance_b, instance_b_strict
from Optimizer.models import Instance, ItemType, Route


def _two_buildings(replacement_cost, surplus, *, routed=True):
    """Source S, destination D short 2 units of "k". Same setup as the
    decision-table tests."""
    routes = {}
    if routed:
        routes = {("S", "D"): Route("S", "D", 10.0, 72.0, 0.05)}
    return Instance(
        buildings=["S", "D"],
        item_types={"k": ItemType("k", replacement_cost)},
        routes=routes,
        supply={("S", "k"): surplus} if surplus else {},
        demand={("D", "k"): 2},
    )


@pytest.fixture
def scipy_must_not_run(monkeypatch):
    """Make any call to linprog blow up, so a test can prove we stopped
    before SciPy ever saw the instance."""
    def _boom(*args, **kwargs):
        raise AssertionError("linprog was called, but the check should have stopped first")
    monkeypatch.setattr(bb, "linprog", _boom)


def test_no_route_and_no_purchase_is_reported_before_scipy_runs(scipy_must_not_run):
    with pytest.raises(UnfillableShortageError) as caught:
        branch_and_bound(_two_buildings(None, 5, routed=False))

    err = caught.value
    assert err.shortages == [("D", "k", 2)]
    assert "infeasible" in str(err)
    assert "D" in str(err) and "k" in str(err)


def test_it_is_still_a_value_error():
    # The frontend catches ValueError, so the new error has to stay one.
    with pytest.raises(ValueError):
        branch_and_bound(_two_buildings(None, 5, routed=False))


def test_not_enough_reachable_surplus_reports_the_amount_short(scipy_must_not_run):
    # 1 unit can reach D, D needs 2, and k can't be bought: 1 short.
    with pytest.raises(UnfillableShortageError) as caught:
        branch_and_bound(_two_buildings(None, 1))
    assert caught.value.shortages == [("D", "k", 1)]


def test_no_route_but_buyable_is_fine():
    # Can't ship it, but can buy it, so this is a normal plan.
    plan, gap = branch_and_bound(_two_buildings(100.0, 5, routed=False))
    assert sum(plan.acquisitions.values()) == 2
    assert gap == pytest.approx(0.0, abs=1e-9)


def test_every_shortage_is_listed_not_just_the_first():
    instance = Instance(
        buildings=["S", "D1", "D2"],
        item_types={"k": ItemType("k", None), "m": ItemType("m", None)},
        routes={},
        supply={("S", "k"): 5, ("S", "m"): 5},
        demand={("D1", "k"): 2, ("D2", "m"): 3},
    )
    assert find_unfillable_shortages(instance) == [("D1", "k", 2), ("D2", "m", 3)]


@pytest.mark.parametrize("make", [instance_a, instance_b, instance_b_strict])
def test_reference_instances_pass_the_check(make):
    assert find_unfillable_shortages(make()) == []
