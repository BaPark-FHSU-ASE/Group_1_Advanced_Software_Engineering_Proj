import pytest


TEST_FILES = [
    "tests/test_connection.py",
     "tests/test_owner.py",
     "tests/test_owner_repository.py",
     "tests/test_owner_repository_create.py",
     "tests/test_owner_repository_get_by_id.py",
     "tests/test_owner_repository_update.py",
     "tests/test_owner_repository_delete.py",
     "tests/test_business_repository.py",
     "tests/test_business_repository_create.py",
     "tests/test_business_repository_get_by_id.py",
     "tests/test_business_repository_update.py",
     "tests/test_business_repository_delete.py",
     "tests/test_building_repository.py",
     "tests/test_building_repository_create.py",
     "tests/test_building_repository_get_by_id.py",
     "tests/test_building_repository_update.py",
     "tests/test_building_repository_delete.py",
     "tests/test_room_repository.py",
     "tests/test_room_repository_create.py",
     "tests/test_room_repository_get_by_id.py",
     "tests/test_room_repository_update.py",
     "tests/test_room_repository_delete.py",
     "tests/test_storage_repository.py",
     "tests/test_storage_repository_create.py",
     "tests/test_storage_repository_get_by_id.py",
     "tests/test_storage_repository_update.py",
     "tests/test_storage_repository_delete.py",
     "tests/test_item_type_repository.py",
     "tests/test_item_type_repository_create.py",
     "tests/test_item_type_repository_get_by_id.py",
     "tests/test_item_type_repository_update.py",
     "tests/test_item_type_repository_delete.py",
     "tests/test_item_repository.py",
     "tests/test_item_repository_create.py",
     "tests/test_item_repository_get_by_id.py",
     "tests/test_item_repository_update.py",
     "tests/test_item_repository_delete.py",
]

if __name__ == "__main__":
    exit_code = pytest.main(["-v", *TEST_FILES])

    if exit_code == 0:
        print("\nAll tests passed.")
    else:
        print("\nSome tests failed - see output above.")