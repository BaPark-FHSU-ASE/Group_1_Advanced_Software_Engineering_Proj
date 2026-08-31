
from app.repositories import building_repository


def test_get_all_returns_list_of_buildings():
    buildings = building_repository.get_all()

    assert isinstance(buildings, list)
    assert len(buildings) >= 1