"""
Regression check against the project's verified optima. Run from the repo
root (Group_1_Advanced_Software_Engineering_Proj/) as:

    python -m Optimizer.verify

Enumeration runs on both instances. The enumerator is not naive about it:
the useful-route filter cuts instance B from 20 directed routes to 10, and
dispatch-cost dominance skips most of the remaining subsets, so the oracle
settles B in well under a tenth of a second. That is what lets every
procedure here be checked against a brute-forced answer rather than against
a number copied out of a document.

It does not scale, and is not meant to. At eight buildings m = 56 and the
subset space is hopeless, which is the whole reason branch_and_bound exists.
"""

from __future__ import annotations

import math

from .enumerate_bruteforce import enumerate_bruteforce
from .instances import (
    INSTANCE_A_NEAREST_SOURCE_COST,
    INSTANCE_A_OPTIMAL_COST,
    INSTANCE_B_NEAREST_SOURCE_COST,
    INSTANCE_B_OPTIMAL_COST,
    INSTANCE_B_STRICT_COST,
    instance_a,
    instance_b,
    instance_b_strict,
)
from .nearest_source import nearest_source_first
from .branch_and_bound import branch_and_bound


def _check(label: str, got: float, expected: float) -> None:
    ok = math.isclose(got, expected, abs_tol=0.02)
    mark = "OK  " if ok else "FAIL"
    print(f"  [{mark}] {label}: got ${got:.2f}, expected ${expected:.2f}")


def check_instance_a() -> None:
    print("Instance A (3 sites, 2 item types)")
    inst = instance_a()

    baseline = nearest_source_first(inst)
    _check("nearest_source_first", baseline.total_cost, INSTANCE_A_NEAREST_SOURCE_COST)

    brute = enumerate_bruteforce(inst)
    _check("enumerate_bruteforce", brute.total_cost, INSTANCE_A_OPTIMAL_COST)

    bnb_plan, gap = branch_and_bound(inst)
    _check(f"branch_and_bound (gap={gap:.4f})", bnb_plan.total_cost, INSTANCE_A_OPTIMAL_COST)
    print(bnb_plan.describe(inst))
    print()


def check_instance_b() -> None:
    print("Instance B (5 sites, 6 item types) - the reference instance")
    inst = instance_b()

    baseline = nearest_source_first(inst)
    _check("nearest_source_first", baseline.total_cost, INSTANCE_B_NEAREST_SOURCE_COST)

    brute = enumerate_bruteforce(inst)
    _check("enumerate_bruteforce", brute.total_cost, INSTANCE_B_OPTIMAL_COST)

    bnb_plan, gap = branch_and_bound(inst, deadline_seconds=30.0)
    _check(f"branch_and_bound (gap={gap:.4f})", bnb_plan.total_cost, INSTANCE_B_OPTIMAL_COST)
    print(bnb_plan.describe(inst))
    print()

    strict = instance_b_strict()
    strict_brute = enumerate_bruteforce(strict)
    _check("enumerate_bruteforce, strict", strict_brute.total_cost, INSTANCE_B_STRICT_COST)

    strict_plan, strict_gap = branch_and_bound(strict, deadline_seconds=30.0)
    _check(f"branch_and_bound, strict (gap={strict_gap:.4f})", strict_plan.total_cost, INSTANCE_B_STRICT_COST)
    print(strict_plan.describe(strict))
    print()


if __name__ == "__main__":
    check_instance_a()
    check_instance_b()
