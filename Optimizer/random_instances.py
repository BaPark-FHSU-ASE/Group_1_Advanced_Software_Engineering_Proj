"""
Random instances for testing and benchmarking the optimizer.

The two hand-built instances in instances.py are too easy - branch and
bound solves them at the root node, so the branching code never actually
ran during testing. This generates lots of small random problems so the
search gets exercised for real. The benchmark uses it too, just with
bigger sizes.

How an instance gets built:
  - buildings are dropped at random spots on a 100 x 100 mile grid
  - every ordered pair of buildings gets a route, priced the same way as
    the Section X example ($60 + $1.20 per mile to dispatch, $0.05 per
    unit-mile to handle)
  - each building/type cell is a surplus about 30% of the time, a
    shortage about 25% of the time, and empty otherwise
  - each item type can be bought with probability p_acquire

Nothing here is used in production.

It's all driven by the rng you pass in, so the same seed gives the same
instance every time. If a test fails you can rerun that exact case.
"""

from __future__ import annotations

import random

from .models import Instance, ItemType, Route


def random_instance(
    rng: random.Random, n_buildings: int, n_types: int, p_acquire: float = 0.5
) -> Instance:
    buildings = [f"b{i}" for i in range(n_buildings)]
    types = [f"k{k}" for k in range(n_types)]
    pos = {b: (rng.uniform(0, 100), rng.uniform(0, 100)) for b in buildings}

    routes = {}
    for i in buildings:
        for j in buildings:
            if i == j:
                continue
            (xi, yi), (xj, yj) = pos[i], pos[j]
            # +1 mile so two buildings that land on top of each other
            # still have a real distance between them
            miles = round(((xi - xj) ** 2 + (yi - yj) ** 2) ** 0.5 + 1.0, 1)
            routes[(i, j)] = Route(i, j, miles, round(60 + 1.2 * miles, 2), 0.05)

    item_types = {
        k: ItemType(k, round(rng.uniform(30, 600), 2) if rng.random() < p_acquire else None)
        for k in types
    }

    supply: dict[tuple[str, str], int] = {}
    demand: dict[tuple[str, str], int] = {}
    for b in buildings:
        for k in types:
            r = rng.random()
            if r < 0.30:
                supply[(b, k)] = rng.randint(1, 4)
            elif r < 0.55:
                demand[(b, k)] = rng.randint(1, 3)

    # If a type can't be bought, the only way to fill its shortages is
    # surplus from somewhere else. Cut those shortages down to what the
    # surplus can cover, otherwise the instance has no answer and the
    # back-to-back test can't compare anything.
    for k in types:
        if item_types[k].replacement_cost is not None:
            continue
        available = sum(q for (_, kk), q in supply.items() if kk == k)
        for key in [key for key in demand if key[1] == k]:
            take = min(demand[key], available)
            available -= take
            if take:
                demand[key] = take
            else:
                del demand[key]

    return Instance(buildings, item_types, routes, supply, demand)
