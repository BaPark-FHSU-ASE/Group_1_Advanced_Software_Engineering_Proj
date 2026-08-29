import pytest


TEST_FILES = [
    "tests/test_connection.py",
     "tests/test_owner.py",
     "tests/test_owner_repository.py",
]

if __name__ == "__main__":
    exit_code = pytest.main(["-v", *TEST_FILES])

    if exit_code == 0:
        print("\nAll tests passed.")
    else:
        print("\nSome tests failed - see output above.")