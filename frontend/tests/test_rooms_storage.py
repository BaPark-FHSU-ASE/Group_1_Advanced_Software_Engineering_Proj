"""
Tests for db.add_room() and db.add_storage().

Owner 1 is the seeded account (dale@prairieroofing.example), who owns
building 1. Owner 999999 doesn't exist, which is how "someone else's
building" looks from the outside.
"""

import pytest

import db

OWNER = 1
OTHER_OWNER = 999999


def test_add_room_shows_up_on_building_page():
    db.add_room(OWNER, 1, "Test room A")
    rooms = db.get_building(1)["rooms"]
    assert any(r["name"] == "Test room A" for r in rooms)


def test_add_room_rejects_building_not_owned():
    with pytest.raises(db.NotFoundOrNotOwned):
        db.add_room(OTHER_OWNER, 1, "Should not exist")


def test_add_room_rejects_missing_building():
    with pytest.raises(db.NotFoundOrNotOwned):
        db.add_room(OWNER, 999999, "Should not exist")


def test_add_storage_to_new_room():
    room_id = db.add_room(OWNER, 1, "Test room B")
    storage_id, building_id = db.add_storage(OWNER, room_id, "Gear cage")
    assert building_id == 1
    room = next(r for r in db.get_building(1)["rooms"] if r["id"] == room_id)
    storage = next(s for s in room["storages"] if s["id"] == storage_id)
    # Not one of the suggested types - any type is allowed (NF-REQ-1)
    assert storage["type"] == "Gear cage"
    assert storage["item_count"] == 0


def test_add_storage_rejects_room_not_owned():
    with pytest.raises(db.NotFoundOrNotOwned):
        db.add_storage(OTHER_OWNER, 1, "Locker")
