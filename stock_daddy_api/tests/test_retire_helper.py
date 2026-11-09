from app.retire_helper import describe_inside


def test_describe_inside_reads_naturally():
    assert describe_inside({"items": 1}) == "1 item"
    assert describe_inside({"storage_units": 3, "items": 41}) == "3 storage units and 41 items"
    assert describe_inside({"rooms": 2, "storage_units": 1, "items": 40}) == (
        "2 rooms, 1 storage unit and 40 items"
    )