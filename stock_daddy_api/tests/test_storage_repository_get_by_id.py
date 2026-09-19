from app.repositories import storage_repository


def test_get_by_id_returns_matching_storage():
    storage = storage_repository.get_by_id(1)

    assert storage is not None
    assert storage.storage_id == 1


def test_get_by_id_returns_none_for_missing_storage():
    storage = storage_repository.get_by_id(9999)

    assert storage is None