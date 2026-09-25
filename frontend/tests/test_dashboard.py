"""
Tests for db.get_dashboard_hierarchy().
"""

import db


def test_returns_seeded_business():
    businesses = db.get_dashboard_hierarchy()
    assert len(businesses) == 1
    assert businesses[0]["name"] == "Prairie Roofing & Exteriors"


def test_business_has_five_buildings():
    businesses = db.get_dashboard_hierarchy()
    buildings = businesses[0]["buildings"]
    assert len(buildings) == 5


def test_building_hierarchy_includes_rooms_and_storages():
    businesses = db.get_dashboard_hierarchy()
    buildings = businesses[0]["buildings"]
    # every seeded building has at least one room, and every room at least
    # one storage unit
    for b in buildings:
        assert len(b["rooms"]) >= 1
        for r in b["rooms"]:
            assert len(r["storages"]) >= 1


def test_storage_item_counts_are_nonnegative_integers():
    businesses = db.get_dashboard_hierarchy()
    for b in businesses[0]["buildings"]:
        for r in b["rooms"]:
            for s in r["storages"]:
                assert isinstance(s["item_count"], int)
                assert s["item_count"] >= 0
