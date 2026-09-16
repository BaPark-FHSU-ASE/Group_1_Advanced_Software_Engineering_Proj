"""
Tests for db.get_items() and db.get_item_detail().
"""

import db


def test_get_items_returns_all_ninety_two_items():
    items = db.get_items()
    assert len(items) == 92


def test_in_transit_item_shows_no_current_location():
    items = db.get_items()
    in_transit = [i for i in items if i["status"] == "In Transit"]
    assert len(in_transit) == 1
    item = in_transit[0]
    assert item["building"] == "In transit"
    assert item["room"] == "—"
    assert item["storage"] == "—"


def test_get_item_detail_returns_none_for_missing_item():
    assert db.get_item_detail(999999) is None


def test_get_item_detail_includes_movement_history():
    # Item 1 (Nail Gun #1) has at least its initial placement recorded.
    item = db.get_item_detail(1)
    assert item is not None
    assert item["name"] == "Nail Gun #1"
    assert len(item["movement_history"]) >= 1
    assert item["movement_history"][0]["to"] != "—"


def test_movement_history_is_most_recent_first():
    item = db.get_item_detail(1)
    dates = [m["date"] for m in item["movement_history"]]
    assert dates == sorted(dates, reverse=True)
