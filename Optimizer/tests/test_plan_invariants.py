"""
Invariants every Plan must satisfy regardless of which procedure produced
it. These are what the presentation layer relies on: REQ-19 needs dispatch
and handling separable per trip, and REQ-24 needs acquisition reported
apart from transfer cost.
"""

from Optimizer.enumerate_bruteforce import enumerate_bruteforce
from Optimizer.instances import instance_a, instance_b, instance_b_strict
from Optimizer.nearest_source import nearest_source_first
from Optimizer.residual import solve_residual

TOL = 0.005


def _every_plan():
    """(label, instance, plan) for each procedure on each instance."""
    for name, instance in (
        ("A", instance_a()),
        ("B", instance_b()),
        ("B-strict", instance_b_strict()),
    ):
        yield f"enumerate/{name}", instance, enumerate_bruteforce(instance)
        yield f"nearest/{name}", instance, nearest_source_first(instance)
        yield (
            f"residual-all/{name}",
            instance,
            solve_residual(instance, instance.route_set()),
        )


def test_trip_total_is_dispatch_plus_handling():
    for label, _instance, plan in _every_plan():
        assert plan is not None, label
        for trip in plan.trips:
            expected = trip.dispatch_cost + trip.handling_cost
            assert abs(trip.total_cost - expected) < TOL, label


def test_acquisition_cost_is_the_remainder_after_dispatch_and_handling():
    """REQ-19 / REQ-24: the three cost components must add up exactly, or
    the UI cannot show them apart without the figures disagreeing."""
    for label, instance, plan in _every_plan():
        assert plan is not None, label
        dispatch = sum(
            instance.routes[route].fixed_dispatch_cost
            for route in plan.opened_routes
        )
        handling = sum(trip.handling_cost for trip in plan.trips)
        remainder = plan.total_cost - dispatch - handling
        assert abs(plan.acquisition_cost(instance) - remainder) < TOL, label


def test_strict_instance_never_acquires():
    """A4 strict variant: c_k is infinite for every type, so every shortage
    must be met by transfer and nothing may be bought."""
    for label, _instance, plan in _every_plan():
        if not label.endswith("B-strict"):
            continue
        assert plan is not None, label
        assert plan.acquisitions == {}, label
