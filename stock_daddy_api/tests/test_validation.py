
import pytest

from app.Validation_Helper import ValidationError, check_fields


def test_good_values_come_back():
    data = {"name": "Hays Depot", "owner_id": 3}
    assert check_fields(data, required={"name": str, "owner_id": int}) == data


def test_text_is_stripped():
    clean = check_fields({"name": "  Hays Depot  "}, required={"name": str})
    assert clean["name"] == "Hays Depot"


def test_missing_required_field():
    with pytest.raises(ValidationError, match="state is required"):
        check_fields({"city": "Hays"}, required={"state": str, "city": str})


def test_null_required_field():
    with pytest.raises(ValidationError, match="owner_id is required"):
        check_fields({"owner_id": None}, required={"owner_id": int})


def test_blank_required_text():
    with pytest.raises(ValidationError, match="name is required"):
        check_fields({"name": "   "}, required={"name": str})


def test_text_where_number_expected():
    with pytest.raises(ValidationError, match="owner_id must be a whole number"):
        check_fields({"owner_id": "3"}, required={"owner_id": int})


def test_true_is_not_a_whole_number():
    with pytest.raises(ValidationError, match="owner_id must be a whole number"):
        check_fields({"owner_id": True}, required={"owner_id": int})


def test_decimal_is_not_a_whole_number():
    with pytest.raises(ValidationError, match="owner_id must be a whole number"):
        check_fields({"owner_id": 1.5}, required={"owner_id": int})


def test_number_where_text_expected():
    with pytest.raises(ValidationError, match="name must be text"):
        check_fields({"name": 5}, required={"name": str})


def test_float_accepts_whole_and_decimal_numbers():
    assert check_fields({"cost": 5}, required={"cost": float}) == {"cost": 5}
    assert check_fields({"cost": 5.25}, required={"cost": float}) == {"cost": 5.25}


def test_float_rejects_text_and_true():
    for bad in ("5.25", True):
        with pytest.raises(ValidationError, match="cost must be a number"):
            check_fields({"cost": bad}, required={"cost": float})


def test_missing_or_null_optional_field_is_left_out():
    optional = {"description": str}
    assert check_fields({}, optional=optional) == {}
    assert check_fields({"description": None}, optional=optional) == {}


def test_optional_field_is_still_type_checked():
    with pytest.raises(ValidationError, match="storage_id must be a whole number"):
        check_fields({"storage_id": "abc"}, optional={"storage_id": int})


def test_every_problem_is_reported_together():
    with pytest.raises(ValidationError) as caught:
        check_fields({"owner_id": "x"}, required={"name": str, "owner_id": int})
    assert caught.value.message == "name is required; owner_id must be a whole number"
    assert caught.value.status_code == 400


def test_unknown_fields_are_ignored():
    clean = check_fields({"name": "A", "junk": 1}, required={"name": str})
    assert clean == {"name": "A"}