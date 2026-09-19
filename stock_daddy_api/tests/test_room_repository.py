
from app.repositories import room_repository


def test_get_all_returns_list_of_rooms():
    rooms = room_repository.get_all()

    assert isinstance(rooms, list)
    assert len(rooms) >= 1