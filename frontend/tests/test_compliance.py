"""Surplus & Shortage and the past-service-life list, against a fake API."""

from tests.conftest import page_text


def test_compliance_page_shows_variances(client, api):
    text = page_text(client.get("/compliance"))
    assert api.called("get_compliance") == [(1,)]
    assert "-2 shortage" in text and "+4 surplus" in text


def test_building_names_link_to_their_page(client, api):
    assert 'href="/building/2"' in client.get("/compliance").get_data(as_text=True)


def test_expired_items_listed(client, api):
    text = page_text(client.get("/compliance"))
    assert api.called("get_expired_items") == [(1,)]
    assert "Past Service Life" in text
    assert "760 days" in text and "730 days" in text and "30 days" in text


def test_no_expired_items(client, api):
    api.returns["get_expired_items"] = []
    assert "No items are past their service life." in page_text(client.get("/compliance"))


def test_empty_compliance(client, api):
    api.returns["get_compliance"] = []
    assert "No compliance data available." in page_text(client.get("/compliance"))


def test_redistribute_button_is_owner_only(client, employee, api):
    assert "Generate Redistribution Plan" in page_text(client.get("/compliance"))
    assert "Generate Redistribution Plan" not in page_text(employee.get("/compliance"))
