"""
Checks for shortages that can't be filled before we try to solve anything
(DEF-1).

A shortage can be filled two ways: ship spare units in from buildings
that have a route to it, or buy new ones. If the item can't be bought and
not enough spare units can reach it, there's no plan. Before this check,
the worst case (no route and no way to buy) went to linprog with zero
variables and the owner just saw SciPy's "Invalid input" error.

This only catches shortages that are impossible by themselves. If two
shortages are fighting over the same few spare units, the solver still
has to figure that out, and it reports it as "infeasible" like before.

Requirements traced: REQ-24 (buy vs. transfer), use case extension 5a
(shortage can't be met either way).
"""

from __future__ import annotations

from .models import Instance

# (building, item type, how many units short)
Shortage = tuple[str, str, int]


class UnfillableShortageError(ValueError):
    """A shortage can't be filled by transfer or by buying new.

    Subclass of ValueError so the frontend's existing `except ValueError`
    still catches it. `shortages` has the list so the API can send it back
    later without having to parse the message.
    """

    def __init__(self, shortages: list[Shortage]):
        self.shortages = shortages
        details = "; ".join(
            f"building {j} is short {qty} of item type {k}, and not enough spare "
            f"stock can reach it by route and it has no replacement cost"
            for j, k, qty in shortages
        )
        super().__init__(f"instance is infeasible: {details}")


def find_unfillable_shortages(instance: Instance) -> list[Shortage]:
    """Shortages that can't be covered even with all the spare stock that
    can reach them. Empty list = nothing obviously wrong."""
    unfillable = []
    for (j, k), needed in sorted(instance.demand.items()):
        if needed <= 0 or instance.item_types[k].replacement_cost is not None:
            continue  # nothing needed, or we can just buy it
        reachable = sum(
            qty
            for (i, kk), qty in instance.supply.items()
            if kk == k and qty > 0 and (i, j) in instance.routes
        )
        if reachable < needed:
            unfillable.append((j, k, needed - reachable))
    return unfillable


def check_fillable(instance: Instance) -> None:
    """Raise UnfillableShortageError if any shortage can't be filled."""
    unfillable = find_unfillable_shortages(instance)
    if unfillable:
        raise UnfillableShortageError(unfillable)
