from app.repositories import room_repository


def test_get_by_id_returns_matching_room():
    room = room_repository.get_by_id(1)

    assert room is not None
    assert room.room_id == 1


def test_get_by_id_returns_none_for_missing_room():
    room = room_repository.get_by_id(9999)

    assert room is None