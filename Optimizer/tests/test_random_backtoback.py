"""
Compares branch_and_bound against the brute-force enumerator on a large
batch of random instances, and checks every plan against constraints
C1-C3 from Section 10b while it's at it.

I added this after looking at branch coverage. The reference instances in
instances.py get solved at the root node, so the part of the search that
actually branches never ran in any test. Random instances fix that. Not
all of them branch, but enough of them do.

Instances are kept at 3-5 buildings so the enumerator can still solve
each one in reasonable time.
"""

import random

import pytest

from Optimizer.branch_and_bound import branch_and_bound
from Optimizer.enumerate_bruteforce import enumerate_bruteforce
from Optimizer.random_instances import random_instance

TOL = 0.005
SEED = 841
N_INSTANCES = 200


def _cases():
    rng = random.Random(SEED)
    out = []
    for n in range(N_INSTANCES):
        instance = random_instance(rng, rng.randint(3, 5), rng.randint(1, 4))
        # an instance with no shortages has nothing to solve, so skip it
        if instance.demand:
            out.append(pytest.param(instance, id=f"seed{SEED}-{n}"))
    return out


CASES = _cases()


@pytest.mark.parametrize("instance", CASES)
def test_branch_and_bound_matches_the_oracle(instance):
    oracle = enumerate_bruteforce(instance)
    plan, gap = branch_and_bound(instance)
    assert oracle is not None
    assert abs(plan.total_cost - oracle.total_cost) < TOL
    assert gap == pytest.approx(0.0, abs=1e-9)


@pytest.mark.parametrize("instance", CASES)
def test_plan_satisfies_c1_c2_c3(instance):
    plan, _gap = branch_and_bound(instance)

    # C1: nobody ships more than their shippable surplus
    for (i, k), surplus in instance.supply.items():
        shipped = sum(t.units_by_type.get(k, 0) for t in plan.trips if t.origin == i)
        assert shipped <= surplus

    # C2: every shortage is filled exactly, by transfers plus purchases
    for (j, k), shortage in instance.demand.items():
        arrived = sum(t.units_by_type.get(k, 0) for t in plan.trips if t.dest == j)
        assert arrived + plan.acquisitions.get((j, k), 0) == shortage

    # C3: trips only run on routes that exist and were actually opened
    for trip in plan.trips:
        assert (trip.origin, trip.dest) in plan.opened_routes
        assert (trip.origin, trip.dest) in instance.routes
