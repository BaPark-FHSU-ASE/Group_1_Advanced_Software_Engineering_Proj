from app.repositories import business_repository


def test_get_by_id_returns_matching_business():
    business = business_repository.get_by_id(1)

    assert business is not None
    assert business.business_id == 1


def test_get_by_id_returns_none_for_missing_business():
    business = business_repository.get_by_id(9999)

    assert business is None