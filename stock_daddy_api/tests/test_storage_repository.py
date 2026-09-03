from app.repositories import storage_repository


def test_get_all_returns_list_of_storage_units():
    storage_units = storage_repository.get_all()

    assert isinstance(storage_units, list)
    assert len(storage_units) >= 1