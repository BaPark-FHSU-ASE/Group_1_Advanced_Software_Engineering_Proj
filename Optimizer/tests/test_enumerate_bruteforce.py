"""
The enumeration oracle against all three reference optima, including the
exact route sets. These are the figures every other procedure is certified
against, so a failure here invalidates the rest of the suite.
"""

from Optimizer.enumerate_bruteforce import enumerate_bruteforce, useful_routes
from Optimizer.instances import (
    INSTANCE_A_OPTIMAL_COST,
    INSTANCE_B_OPTIMAL_COST,
    INSTANCE_B_STRICT_COST,
    instance_a,
    instance_b,
    instance_b_strict,
)

TOL = 0.005


def test_instance_a_optimum_and_exact_route_set():
    plan = enumerate_bruteforce(instance_a())
    assert plan is not None
    assert abs(plan.total_cost - INSTANCE_A_OPTIMAL_COST) < TOL
    assert plan.opened_routes == frozenset({("B", "A"), ("A", "C")})


def test_instance_b_optimum_opens_three_routes():
    plan = enumerate_bruteforce(instance_b())
    assert plan is not None
    assert abs(plan.total_cost - INSTANCE_B_OPTIMAL_COST) < TOL
    assert len(plan.opened_routes) == 3


def test_instance_b_strict_optimum_opens_four_routes():
    """With acquisition unavailable everywhere (A4 strict), one extra route
    has to open to carry what would otherwise have been bought."""
    plan = enumerate_bruteforce(instance_b_strict())
    assert plan is not None
    assert abs(plan.total_cost - INSTANCE_B_STRICT_COST) < TOL
    assert len(plan.opened_routes) == 4


def test_useful_route_filter_never_discards_an_optimal_route():
    """The filter is the reason instance B is tractable at all. If it ever
    drops a route the optimum needs, every result above becomes wrong."""
    for instance in (instance_a(), instance_b(), instance_b_strict()):
        plan = enumerate_bruteforce(instance)
        assert plan.opened_routes <= frozenset(useful_routes(instance))
