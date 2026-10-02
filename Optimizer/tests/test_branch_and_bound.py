"""
The production search against the same optima the oracle certifies.

Section 11e requires every solution procedure to reproduce the reference
costs, and branch_and_bound is the one that has to be believed at sizes the
enumerator cannot reach. So it is checked two ways here: against the stored
constants, and against enumerate_bruteforce run on the same instance, which
is the check that keeps meaning something as further instances are added.

A gap of zero is part of the assertion, not a detail. NF-REQ-8 lets the
search return early with a positive gap; a run that quietly did so while
landing on the right cost would still be a regression in the bound.
"""

import pytest

from Optimizer.branch_and_bound import branch_and_bound
from Optimizer.enumerate_bruteforce import enumerate_bruteforce
from Optimizer.instances import (
    INSTANCE_A_OPTIMAL_COST,
    INSTANCE_B_OPTIMAL_COST,
    INSTANCE_B_STRICT_COST,
    instance_a,
    instance_b,
    instance_b_strict,
)

TOL = 0.005

CASES = [
    ("A", instance_a, INSTANCE_A_OPTIMAL_COST, 2),
    ("B", instance_b, INSTANCE_B_OPTIMAL_COST, 3),
    ("B-strict", instance_b_strict, INSTANCE_B_STRICT_COST, 4),
]


@pytest.mark.parametrize("label, build, expected, n_routes", CASES)
def test_reproduces_the_reference_optimum(label, build, expected, n_routes):
    plan, gap = branch_and_bound(build())
    assert abs(plan.total_cost - expected) < TOL, label
    assert len(plan.opened_routes) == n_routes, label


@pytest.mark.parametrize("label, build, expected, n_routes", CASES)
def test_certifies_optimality_with_a_zero_gap(label, build, expected, n_routes):
    """The tree is exhausted on instances this small, so the bound must
    close. A positive gap here means the search stopped early."""
    _plan, gap = branch_and_bound(build())
    assert gap == pytest.approx(0.0, abs=1e-9), label


@pytest.mark.parametrize("label, build, expected, n_routes", CASES)
def test_agrees_with_the_enumeration_oracle(label, build, expected, n_routes):
    """The check that survives new instances: the two procedures must land
    on the same cost, whatever that cost turns out to be."""
    instance = build()
    oracle = enumerate_bruteforce(instance)
    plan, _gap = branch_and_bound(instance)
    assert oracle is not None, label
    assert abs(plan.total_cost - oracle.total_cost) < TOL, label


def test_deadline_is_respected_and_reports_a_gap():
    """NF-REQ-8: a deadline short enough to bite must still return a usable
    plan rather than raising or returning nothing, with the gap bounding
    how far it may be from optimal."""
    plan, gap = branch_and_bound(instance_b(), deadline_seconds=0.0)
    assert plan is not None
    assert gap >= 0.0
    # Nothing was explored, so the returned plan is the greedy seed.
    assert plan.total_cost >= INSTANCE_B_OPTIMAL_COST - TOL


def test_never_returns_a_plan_that_costs_less_than_the_optimum():
    """A plan cheaper than the certified optimum is not a better answer, it
    is an invalid one - the guard against a search that drops a constraint."""
    for label, build, expected, _n in CASES:
        plan, _gap = branch_and_bound(build())
        assert plan.total_cost >= expected - TOL, label
