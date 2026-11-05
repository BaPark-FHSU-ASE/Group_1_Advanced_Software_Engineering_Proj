"""
A quick check, before any solving, for shortages that can't possibly be
filled (DEF-1).

A shortage of type k at building j has two ways out: ship units in from
buildings that have spare k and a route to j, or buy new ones. If k has no
replacement cost and the spare units that can reach j don't add up to the
shortage, there's no plan, and it's better to say so plainly than to let
the solver fall over. Before this existed, the worst version of it (no
route at all and no way to buy) reached linprog with zero variables, and
the owner saw SciPy's "Invalid input" error instead of anything useful.

This only catches shortages that are unfillable on their own. Two
shortages competing for the same few spare units can still turn out
infeasible together; the LP catches that case and branch_and_bound reports
it as "infeasible" like before.

Requirements traced: REQ-24 (buy vs. transfer), use-case extension 5a
(a shortage that can be met neither way).
"""

from __future__ import annotations

from .models import Instance

# (building, item type, units that can't be covered)
Shortage = tuple[str, str, int]


class UnfillableShortageError(ValueError):
    """Some shortage can be met neither by transfer nor by buying new.

    It's a ValueError on purpose: the frontend already catches ValueError
    from branch_and_bound, so nothing upstream has to change. `shortages`
    holds the structured list, so the API can return it later instead of
    parsing the message.
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
    """Every shortage that can't be covered even if it got all the spare
    stock that can reach it. Empty list means nothing obviously wrong."""
    unfillable = []
    for (j, k), needed in sorted(instance.demand.items()):
        if needed <= 0 or instance.item_types[k].replacement_cost is not None:
            continue  # nothing needed, or we can always buy it
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
