"""
Timing check for NF-REQ-7 and NF-REQ-8. Run it from the repo root:

    python -m Optimizer.benchmark

NF-REQ-7 says a plan for 10 buildings and 20 item types has to come back
in under 5 seconds, so we time 20 of those and look at the slowest one.
NF-REQ-8 says that at 30 buildings we get a plan (and its gap) within
30 seconds.

The seed is fixed, so every machine solves the same instances. Only the
timings change from one computer to another. The script exits non-zero
when either requirement is missed, which lets us use it as the M-5 check
on optimizer pull requests.
"""

from __future__ import annotations

import random
import statistics
import sys
import time

from .branch_and_bound import branch_and_bound
from .random_instances import random_instance


def _run(rng, n_buildings, n_types, runs, deadline):
    """Solve `runs` random instances and return (seconds, gap) for each."""
    rows = []
    for _ in range(runs):
        instance = random_instance(rng, n_buildings, n_types)
        start = time.monotonic()
        _plan, gap = branch_and_bound(instance, deadline_seconds=deadline)
        rows.append((time.monotonic() - start, gap))
    return rows


def main(runs_7: int = 20, runs_8: int = 3) -> int:
    rng = random.Random(2026)
    ok = True

    rows = _run(rng, 10, 20, runs_7, deadline=30.0)
    times = [t for t, _ in rows]
    over = sum(t >= 5.0 for t in times)
    print(f"NF-REQ-7  10 bldg x 20 types, {runs_7} instances")
    print(f"  median {statistics.median(times):.2f} s   worst {max(times):.2f} s   "
          f"over 5 s: {over}   max gap {max(g for _, g in rows):.1%}")
    ok &= over == 0

    rows = _run(rng, 30, 20, runs_8, deadline=30.0)
    print(f"NF-REQ-8  30 bldg x 20 types, {runs_8} instances")
    for t, g in rows:
        print(f"  {t:.2f} s   gap {g:.1%}")
    ok &= all(t <= 30.0 for t, _ in rows)

    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
