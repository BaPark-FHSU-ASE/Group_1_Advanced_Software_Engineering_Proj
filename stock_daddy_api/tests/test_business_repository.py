from app.repositories import business_repository


def test_get_all_returns_list_of_businesses():
    businesses = business_repository.get_all()

    assert isinstance(businesses, list)
    assert len(businesses) >= 1


