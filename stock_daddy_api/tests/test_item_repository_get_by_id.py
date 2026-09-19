from app.repositories import item_repository


def test_get_by_id_returns_matching_item():
    item = item_repository.get_by_id(1)

    assert item is not None
    assert item.item_id == 1


def test_get_by_id_returns_none_for_missing_item():
    item = item_repository.get_by_id(999999)

    assert item is None