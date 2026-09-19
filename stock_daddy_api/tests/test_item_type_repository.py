from app.repositories import item_type_repository


def test_get_all_returns_list_of_item_types():
    item_types = item_type_repository.get_all()

    assert isinstance(item_types, list)
    assert len(item_types) >= 1