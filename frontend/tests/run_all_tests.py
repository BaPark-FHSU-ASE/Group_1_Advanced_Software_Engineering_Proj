"""Run every frontend test file.

Picks up any test_*.py in this folder automatically, so new test files
don't need to be added to a list here.
"""

from pathlib import Path
import sys

import pytest


TESTS_DIR = Path(__file__).resolve().parent

if __name__ == "__main__":
    exit_code = pytest.main(["-v", str(TESTS_DIR)])

    if exit_code == 0:
        print("\nAll tests passed.")
    else:
        print("\nSome tests failed - see output above.")

    sys.exit(exit_code)
