"""
Glue between the database, Scott's optimizer (Optimizer/), and the
/redistribute page.

    db.get_optimizer_inputs(owner_id)   plain dicts from SQLite
        -> build_instance()             Optimizer.models.Instance
        -> branch_and_bound()           optimal plan (REQ-18) + gap (NF-REQ-8)
        -> nearest_source_first()       greedy baseline (REQ-20)
        -> to_view()                    the dict redistribute.html renders

The optimizer itself is not changed here; this module only translates in
and out of it. Buildings and item types are keyed by their database ids
(as strings) inside the Instance, and translated back to labels for
display, so the optimizer never sees a display name.

The Optimizer package lives at the repo root, one level above frontend/,
so the root is added to sys.path before importing it. That keeps
`python app.py` working from inside frontend/ with no install step.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from Optimizer.branch_and_bound import branch_and_bound  # noqa: E402
from Optimizer.models import Instance, ItemType, Plan, Route  # noqa: E402
from Optimizer.nearest_source import nearest_source_first  # noqa: E402

import db  # noqa: E402

# A web request shouldn't hang for the optimizer's 30 s default. If the
# deadline hits first, the best plan found so far is still returned and the
# page reports the gap instead of calling it optimal (NF-REQ-8).
DEADLINE_SECONDS = 10.0

# Costs come from SQLite REAL columns, so compare with a tolerance.
_EPS = 1e-6


class NoFeasiblePlan(Exception):
    """Some shortage can be met neither by a transfer nor by buying new."""


def build_instance(inputs: dict) -> tuple[Instance, dict, dict]:
    """Turn db.get_optimizer_inputs() output into an Optimizer Instance.

    Returns (instance, building_labels, type_names), where the two dicts map
    the Instance's string keys back to display text.
    """
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


def to_view(plan: Plan, instance: Instance, building_labels: dict, type_names: dict) -> dict:
    """Shape a Plan into what redistribute.html expects."""
    trips = []
    for t in sorted(plan.trips, key=lambda t: (building_labels[t.origin], building_labels[t.dest])):
        trips.append({
            "from": building_labels[t.origin],
            "to": building_labels[t.dest],
            "items": [
                {"qty": qty, "type": type_names[k]}
                for k, qty in sorted(t.units_by_type.items(), key=lambda kv: type_names[kv[0]])
                if qty > 0
            ],
            "dispatch_cost": t.dispatch_cost,
            "handling_cost": t.handling_cost,
        })

    acquisitions = []
    for (j, k), qty in sorted(plan.acquisitions.items(),
                              key=lambda kv: (building_labels[kv[0][0]], type_names[kv[0][1]])):
        if qty > 0:
            unit = instance.item_types[k].replacement_cost
            acquisitions.append({
                "building": building_labels[j],
                "type": type_names[k],
                "qty": qty,
                "unit_cost": unit,
                "cost": unit * qty,
            })

    return {"trips": trips, "acquisitions": acquisitions}


def generate_plan(owner_id: int, deadline_seconds: float = DEADLINE_SECONDS) -> dict:
    """Run the optimizer for one owner and return the page's plan dict.

    Raises NoFeasiblePlan if no plan exists at all.
    """
    instance, building_labels, type_names = build_instance(db.get_optimizer_inputs(owner_id))

    if not instance.demand:
        # Nothing is short anywhere, so there is nothing to move.
        return {
            "generated": True,
            "no_shortages": True,
            "trips": [],
            "acquisitions": [],
            "total_cost": 0.0,
            "transfer_cost": 0.0,
            "acquisition_cost": 0.0,
            "greedy_cost": 0.0,
            "gap": 0.0,
            "optimal": True,
        }

    try:
        plan, gap = branch_and_bound(instance, deadline_seconds=deadline_seconds)
    except ValueError as exc:
        # branch_and_bound raises ValueError when even the LP relaxation is
        # infeasible, or when the deadline passes with no plan at all.
        raise NoFeasiblePlan(str(exc)) from exc

    baseline = nearest_source_first(instance)
    view = to_view(plan, instance, building_labels, type_names)
    acquisition_cost = plan.acquisition_cost(instance)

    return {
        "generated": True,
        "no_shortages": False,
        "trips": view["trips"],
        "acquisitions": view["acquisitions"],
        "total_cost": plan.total_cost,
        "transfer_cost": plan.total_cost - acquisition_cost,
        "acquisition_cost": acquisition_cost,
        # None when the greedy method gets stuck; the page then hides savings.
        "greedy_cost": None if baseline is None else baseline.total_cost,
        "gap": gap,
        "optimal": gap <= _EPS,
    }
