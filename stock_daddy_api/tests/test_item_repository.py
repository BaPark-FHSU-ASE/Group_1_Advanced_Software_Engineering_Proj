from app.repositories import item_repository


def test_get_all_returns_list_of_items():
    items = item_repository.get_all()

    assert isinstance(items, list)
    assert len(items) >= 1