"""
Tests for db.get_building().
"""

import db


def test_returns_none_for_missing_building():
    assert db.get_building(999999) is None


def test_returns_building_with_compliance_data():
    building = db.get_building(1)
    assert building is not None
    assert "Salina" in building["name"]
    assert len(building["compliance"]) > 0


def test_compliance_rows_have_expected_fields():
    building = db.get_building(1)
    row = building["compliance"][0]
    assert set(row.keys()) == {"item_type", "target", "on_hand", "available", "variance"}


def test_salina_north_nail_gun_matches_known_seed_values():
    # Verified earlier against the live seed data: target 3, on_hand (present) 7,
    # of which only 3 are actually available (4 are In Use).
    building = db.get_building(1)
    nail_gun = next(r for r in building["compliance"] if r["item_type"] == "Nail Gun")
    assert nail_gun["target"] == 3
    assert nail_gun["on_hand"] == 7
    assert nail_gun["available"] == 3
