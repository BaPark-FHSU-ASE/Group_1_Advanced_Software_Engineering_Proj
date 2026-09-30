"""
Runs the whole optimizer suite in one go, mirroring
stock_daddy_api/tests/run_all_tests.py.

Run from the repo root:

    python Optimizer/tests/run_all_tests.py
"""

import pytest

TEST_FILES = [
    "Optimizer/tests/test_residual.py",
    "Optimizer/tests/test_nearest_source.py",
    "Optimizer/tests/test_enumerate_bruteforce.py",
    "Optimizer/tests/test_branch_and_bound.py",
    "Optimizer/tests/test_plan_invariants.py",
]

if __name__ == "__main__":
    exit_code = pytest.main(["-v", *TEST_FILES])

    if exit_code == 0:
        print("\nAll tests passed.")
    else:
        print("\nSome tests failed - see output above.")
