"""
Tests for solve_milp. The decision table and random back-to-back tests
already check it against the brute force solver, so this file is mostly
the reference answers and the deadline stuff (NF-REQ-8, DEF-3).
"""

import random
import time

import pytest

from Optimizer.feasibility import UnfillableShortageError
from Optimizer.instances import instance_a, instance_b, instance_b_strict
from Optimizer.milp_solver import solve_milp
from Optimizer.models import Instance, ItemType
from Optimizer.random_instances import random_instance

TOL = 0.005

# extra time allowed past the deadline, in case the machine is busy
SLACK_SECONDS = 0.3


@pytest.mark.parametrize(
    "make, optimum, routes",
    [(instance_a, 152.99, 2), (instance_b, 575.44, 3), (instance_b_strict, 591.42, 4)],
)
def test_reference_optima(make, optimum, routes):
    plan, gap = solve_milp(make())
    assert abs(plan.total_cost - optimum) < TOL
    assert len(plan.opened_routes) == routes
    assert gap == pytest.approx(0.0, abs=1e-9)


@pytest.fixture(scope="module")
def big_instance():
    # 30 buildings is too big to solve in 1 s, so the deadline has to stop it
    return random_instance(random.Random(7), 30, 20)


def test_deadline_is_a_hard_stop(big_instance):
    start = time.monotonic()
    plan, gap = solve_milp(big_instance, deadline_seconds=1.0)
    elapsed = time.monotonic() - start
    assert elapsed < 1.0 + SLACK_SECONDS
    assert plan.total_cost > 0
    assert 0.0 <= gap <= 1.0


def test_zero_deadline_still_returns_a_plan_and_a_gap(big_instance):
    # like OPT-06: with no time at all we should still get the greedy plan
    # back, with a gap so nobody thinks it's optimal
    plan, gap = solve_milp(big_instance, deadline_seconds=0.0)
    assert plan.trips or plan.acquisitions
    assert gap > 0


def test_no_shortages_means_an_empty_plan():
    instance = Instance(
        buildings=["S", "D"],
        item_types={"k": ItemType("k", 50.0)},
        routes={},
        supply={("S", "k"): 3},
        demand={},
    )
    plan, gap = solve_milp(instance)
    assert plan.trips == [] and plan.acquisitions == {}
    assert plan.total_cost == 0.0 and gap == 0.0


def test_unfillable_shortage_is_reported_clearly():
    instance = Instance(
        buildings=["S", "D"],
        item_types={"k": ItemType("k", None)},
        routes={},
        supply={("S", "k"): 5},
        demand={("D", "k"): 2},
    )
    with pytest.raises(UnfillableShortageError):
        solve_milp(instance)
