"""
The REQ-20 nearest-source baseline against its published figures.

Both constants now reproduce. INSTANCE_B_NEAREST_SOURCE_COST was flagged as
independently unverified when this suite was written; the implementation
here reaches it with seven opened routes, which matches the seven trips
quoted for the same figure in Section 5a of the proposal.
"""

from Optimizer.instances import (
    INSTANCE_A_NEAREST_SOURCE_COST,
    INSTANCE_A_OPTIMAL_COST,
    INSTANCE_B_NEAREST_SOURCE_COST,
    INSTANCE_B_OPTIMAL_COST,
    instance_a,
    instance_b,
)
from Optimizer.nearest_source import nearest_source_first

TOL = 0.005


def test_instance_a_reproduces_the_published_baseline():
    plan = nearest_source_first(instance_a())
    assert plan is not None
    assert abs(plan.total_cost - INSTANCE_A_NEAREST_SOURCE_COST) < TOL


def test_instance_b_reproduces_the_published_baseline():
    plan = nearest_source_first(instance_b())
    assert plan is not None
    assert abs(plan.total_cost - INSTANCE_B_NEAREST_SOURCE_COST) < TOL


def test_instance_a_baseline_opens_three_directed_routes():
    """Both C->A and A->C are opened and each is charged its own dispatch.
    Collapsing them into one undirected route is what would silently make
    this baseline too cheap."""
    plan = nearest_source_first(instance_a())
    assert len(plan.opened_routes) == 3


def test_baseline_is_never_cheaper_than_the_optimum():
    """Catches sign errors and double-counting: a 'baseline' that beats the
    optimum means one of the two is computing cost wrongly."""
    for instance, optimum in (
        (instance_a(), INSTANCE_A_OPTIMAL_COST),
        (instance_b(), INSTANCE_B_OPTIMAL_COST),
    ):
        plan = nearest_source_first(instance)
        assert plan is not None
        assert plan.total_cost >= optimum - TOL
