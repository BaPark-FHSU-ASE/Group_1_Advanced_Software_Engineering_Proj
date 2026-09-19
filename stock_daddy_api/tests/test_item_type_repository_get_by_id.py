from app.repositories import item_type_repository


def test_get_by_id_returns_matching_item_type():
    item_type = item_type_repository.get_by_id(1)

    assert item_type is not None
    assert item_type.item_type_id == 1


def test_get_by_id_returns_none_for_missing_item_type():
    item_type = item_type_repository.get_by_id(9999)

    assert item_type is None