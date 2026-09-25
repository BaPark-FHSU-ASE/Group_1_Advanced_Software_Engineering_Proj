"""
Tests for db.get_compliance_report().
"""

import db


def test_returns_thirty_rows():
    # 5 buildings x 6 item types, one target_quantity row each per the seed data.
    report = db.get_compliance_report()
    assert len(report) == 30


def test_report_rows_have_expected_fields():
    report = db.get_compliance_report()
    row = report[0]
    assert set(row.keys()) == {"building", "item_type", "target", "on_hand", "available", "variance"}


def test_variance_equals_on_hand_minus_target():
    report = db.get_compliance_report()
    for row in report:
        assert row["variance"] == row["on_hand"] - row["target"]


def test_hays_nail_gun_shows_a_shortage():
    # Verified earlier against the live seed data: Hays is short 2 nail guns.
    report = db.get_compliance_report()
    row = next(r for r in report if r["building"] == "Hays" and r["item_type"] == "Nail Gun")
    assert row["target"] == 3
    assert row["on_hand"] == 1
    assert row["variance"] == -2
