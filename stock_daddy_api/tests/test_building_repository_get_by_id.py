from app.repositories import building_repository


def test_get_by_id_returns_matching_building():
    building = building_repository.get_by_id(1)

    assert building is not None
    assert building.building_id == 1


def test_get_by_id_returns_none_for_missing_building():
    building = building_repository.get_by_id(9999)

    assert building is None