"""
Glue between the database and the optimizer for POST /plans.

This used to live in the frontend as redistribution.py. It moved behind the
API in V2 so the frontend never talks to the database or the optimizer
directly. The steps are the same as before:

    plan_repository.get_optimizer_inputs()   plain dicts from SQLite
      -> build_instance()                     an Optimizer Instance
      -> solve_milp()                         best plan + gap (REQ-18, NF-REQ-8)
      -> nearest_source_first()               greedy baseline (REQ-20)
      -> the dict the redistribute page shows

and V2 adds two things on top:
  - which actual items go on each truck (REQ-22)
  - what each filled shortage cost (REQ-21)

The output shape is the one in frontend/API_CONTRACT.md. The extra keys
(method, plan_run_id, and names / item_ids on each item row) are new; the
page ignores keys it doesn't know about.

Requirements traced: REQ-18, REQ-19, REQ-20, REQ-21, REQ-22, REQ-24,
REQ-27, NF-REQ-7, NF-REQ-8.
"""

from __future__ import annotations

import sys
from pathlib import Path

from app.Validation_Helper import ValidationError
from app.repositories import plan_repository

# Optimizer/ sits at the repo root, two levels up from this file.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from Optimizer.feasibility import UnfillableShortageError  # noqa: E402
from Optimizer.milp_solver import solve_milp  # noqa: E402
from Optimizer.models import Instance, ItemType, Route  # noqa: E402
from Optimizer.nearest_source import nearest_source_first  # noqa: E402

# A web request shouldn't sit there for the optimizer's full 30 s. If this
# runs out first we still get the best plan found so far, and the page
# shows the gap instead of calling it optimal (NF-REQ-8).
DEADLINE_SECONDS = 10.0

# costs come from SQLite REAL columns, so compare with a tolerance
_EPS = 1e-6


class NoPlanPossible(ValidationError):
    """Some shortage can't be filled by transfer or by buying. Turned into a
    409 with a sentence the page shows as-is."""

    def __init__(self, message):
        super().__init__(message, 409)


def build_instance(inputs):
    """Turn the repository's dicts into an Instance. Returns
    (instance, building_labels, type_names), where the two dicts map the
    instance's string keys back to names for display."""
    building_labels = {str(b["id"]): b["label"] for b in inputs["buildings"]}
    type_names = {str(t["id"]): t["name"] for t in inputs["item_types"]}

    item_types = {
        str(t["id"]): ItemType(str(t["id"]), t["replacement_cost"])
        for t in inputs["item_types"]
    }
    routes = {}
    for r in inputs["routes"]:
        i, j = str(r["from_id"]), str(r["to_id"])
        routes[(i, j)] = Route(
            i, j, r["distance_miles"], r["fixed_dispatch_cost"], r["cost_per_unit_mile"]
        )

    supply, demand = {}, {}
    for p in inputs["positions"]:
        key = (str(p["building_id"]), str(p["item_type_id"]))
        if p["supply"] > 0:
            supply[key] = p["supply"]
        if p["demand"] > 0:
            demand[key] = p["demand"]

    instance = Instance(
        buildings=list(building_labels),
        item_types=item_types,
        routes=routes,
        supply=supply,
        demand=demand,
    )
    return instance, building_labels, type_names


def generate_plan(user_id):
    """Run the optimizer over every business user_id owns and return the
    plan dict. Raises NoPlanPossible if some shortage can't be filled."""
    business_ids = plan_repository.owned_business_ids(user_id)
    inputs = plan_repository.get_optimizer_inputs(business_ids)
    instance, labels, names = build_instance(inputs)

    if not instance.demand:
        # nothing is short anywhere, so nothing to move
        return {
            "generated": True,
            "no_shortages": True,
            "optimal": True,
            "gap": 0.0,
            "total_cost": 0.0,
            "transfer_cost": 0.0,
            "acquisition_cost": 0.0,
            "greedy_cost": 0.0,
            "trips": [],
            "acquisitions": [],
            "shortage_costs": [],
        }

    try:
        plan, gap = solve_milp(instance, deadline_seconds=DEADLINE_SECONDS)
    except UnfillableShortageError as err:
        raise NoPlanPossible(_explain(err.shortages, labels, names)) from err
    except ValueError as err:
        raise NoPlanPossible(
            "No plan can cover every shortage: at least one can be met "
            "neither by a transfer nor by buying new."
        ) from err

    baseline = nearest_source_first(instance)
    acquisition_cost = plan.acquisition_cost(instance)
    optimal = gap <= _EPS

    result = {
        "generated": True,
        "no_shortages": False,
        "optimal": optimal,
        "gap": gap,
        "method": "milp_optimal" if optimal else "milp_time_limit",
        "total_cost": plan.total_cost,
        "transfer_cost": plan.total_cost - acquisition_cost,
        "acquisition_cost": acquisition_cost,
        # None when the greedy method gets stuck; the page then hides savings
        "greedy_cost": None if baseline is None else baseline.total_cost,
        "trips": _trips(plan, labels, names),
        "acquisitions": _acquisitions(plan, instance, labels, names),
        "shortage_costs": _shortage_costs(plan, instance, labels, names),
    }

    # REQ-27: keep a copy so a plan can be looked at again later. plan_run
    # only has room for one business, so a plan that covers several of
    # the user's businesses is saved under the first one.
    result["plan_run_id"] = plan_repository.save_plan_run(
        business_id=business_ids[0],
        run_by=user_id,
        method=result["method"],
        total_cost=plan.total_cost,
        # if the greedy plan got stuck there's no baseline; the column can't
        # be empty, so store the plan's own cost (savings of 0)
        baseline_cost=plan.total_cost if baseline is None else baseline.total_cost,
        gap=gap,
        plan=result,
    )
    return result


def _trips(plan, labels, names):
    """Trips for the page, with the actual items picked for each (REQ-22).

    Items come from the origin building and must be In Storage and not
    retired. An origin that sends the same type on two trips hands out
    different items on each, so no item is ever on two trucks.
    """
    picked = {}  # (origin, type) -> items still free to hand out
    trips = []
    for t in sorted(plan.trips, key=lambda t: (labels[t.origin], labels[t.dest])):
        rows = []
        for k, qty in sorted(t.units_by_type.items(), key=lambda kv: names[kv[0]]):
            if qty <= 0:
                continue
            free = picked.setdefault(
                (t.origin, k), plan_repository.available_items(int(t.origin), int(k))
            )
            chosen, picked[(t.origin, k)] = free[:qty], free[qty:]
            rows.append({
                "qty": qty,
                "type": names[k],
                "item_ids": [item_id for item_id, _ in chosen],
                "names": [name for _, name in chosen],
            })
        trips.append({
            "from": labels[t.origin],
            "to": labels[t.dest],
            "items": rows,
            "dispatch_cost": t.dispatch_cost,
            "handling_cost": t.handling_cost,
        })
    return trips


def _acquisitions(plan, instance, labels, names):
    rows = []
    for (j, k), qty in sorted(plan.acquisitions.items(),
                              key=lambda kv: (labels[kv[0][0]], names[kv[0][1]])):
        if qty > 0:
            unit = instance.item_types[k].replacement_cost
            rows.append({
                "building": labels[j],
                "type": names[k],
                "qty": qty,
                "unit_cost": unit,
                "cost": unit * qty,
            })
    return rows


def _shortage_costs(plan, instance, labels, names):
    """What each filled shortage cost (REQ-21).

    A trip's cost (dispatch + handling) is split across what it carries in
    proportion to units, so a trip with 3 nail guns and 1 ladder charges
    3/4 of its cost to the nail guns. Anything bought new for the shortage
    is added on top. Rounded to cents, with any leftover cent put on the
    last row so the rows add up exactly to the plan total.
    """
    raw = {}  # (dest, type) -> [cost, qty]
    for t in plan.trips:
        carried = sum(t.units_by_type.values())
        if carried <= 0:
            continue
        for k, qty in t.units_by_type.items():
            if qty > 0:
                row = raw.setdefault((t.dest, k), [0.0, 0])
                row[0] += t.total_cost * qty / carried
                row[1] += qty
    for (j, k), qty in plan.acquisitions.items():
        if qty > 0:
            row = raw.setdefault((j, k), [0.0, 0])
            row[0] += instance.item_types[k].replacement_cost * qty
            row[1] += qty

    keys = sorted(raw, key=lambda key: (labels[key[0]], names[key[1]]))
    costs = [round(raw[key][0], 2) for key in keys]
    if costs:
        costs[-1] = round(costs[-1] + round(plan.total_cost, 2) - round(sum(costs), 2), 2)

    return [
        {
            "building": labels[j],
            "type": names[k],
            "qty": raw[(j, k)][1],
            "cost": cost,
            "cost_per_unit": round(cost / raw[(j, k)][1], 2),
        }
        for (j, k), cost in zip(keys, costs)
    ]


def _explain(shortages, labels, names):
    """Turn the optimizer's list of impossible shortages into sentences."""
    parts = []
    for j, k, qty in shortages:
        item = names.get(k, f"item type {k}")
        parts.append(
            f"{labels.get(j, f'Building {j}')} is short {qty} {item}, but not "
            f"enough spare {item} can reach it on a configured route, and "
            f"{item} has no replacement cost to buy new."
        )
    return " ".join(parts)
