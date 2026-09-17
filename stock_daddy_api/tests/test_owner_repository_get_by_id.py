from app.repositories import owner_repository


def test_get_by_id_returns_matching_owner():
    owner = owner_repository.get_by_id(1)

    assert owner is not None
    assert owner.owner_id == 1
    assert owner.first_name == "Dale"


def test_get_by_id_returns_none_for_missing_owner():
    owner = owner_repository.get_by_id(9999)

    assert owner is None