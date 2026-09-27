"""
solve_residual against the reference instance and the model constraints it
is required to enforce (C1, C2, C3 of Section 10b).
"""

from Optimizer.instances import INSTANCE_A_OPTIMAL_COST, instance_a, instance_b_strict
from Optimizer.residual import solve_residual

TOL = 0.005

# The optimal route set for instance A, per Section X's worked example.
A_OPTIMAL_ROUTES = frozenset({("B", "A"), ("A", "C")})


def test_known_optimal_route_set_reproduces_instance_a_optimum():
    plan = solve_residual(instance_a(), A_OPTIMAL_ROUTES)
    assert plan is not None
    assert abs(plan.total_cost - INSTANCE_A_OPTIMAL_COST) < TOL


def test_every_shortage_is_fully_met():
    """C2: units shipped in plus units acquired equals the shortage."""
    instance = instance_a()
    plan = solve_residual(instance, A_OPTIMAL_ROUTES)

    for (building, item_type), shortage in instance.demand.items():
        shipped_in = sum(
            trip.units_by_type.get(item_type, 0)
            for trip in plan.trips
            if trip.dest == building
        )
        acquired = plan.acquisitions.get((building, item_type), 0)
        assert shipped_in + acquired == shortage


def test_no_building_ships_more_than_its_shippable_surplus():
    """C1: outbound flow of a type never exceeds that building's surplus."""
    instance = instance_a()
    plan = solve_residual(instance, A_OPTIMAL_ROUTES)

    for (building, item_type), surplus in instance.supply.items():
        shipped_out = sum(
            trip.units_by_type.get(item_type, 0)
            for trip in plan.trips
            if trip.origin == building
        )
        assert shipped_out <= surplus


def test_no_flow_on_a_route_outside_the_permitted_set():
    """C3: nothing moves along a route that was not permitted."""
    instance = instance_a()
    plan = solve_residual(instance, A_OPTIMAL_ROUTES)

    for trip in plan.trips:
        assert (trip.origin, trip.dest) in A_OPTIMAL_ROUTES
    assert plan.opened_routes <= A_OPTIMAL_ROUTES


def test_unmeetable_demand_returns_none_rather_than_raising():
    """instance_b_strict has no acquisition option for any type, so with no
    routes permitted its shortages can be met neither way. That is a None,
    not an exception."""
    assert solve_residual(instance_b_strict(), frozenset()) is None
