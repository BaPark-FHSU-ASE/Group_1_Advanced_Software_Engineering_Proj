"""Movement history search and CSV export (REQ-13), against a fake API."""

from tests.conftest import page_text


def test_search_page_lists_movements(client, api):
    text = page_text(client.get("/movements"))
    assert api.called("search_movements") == [(1,)]
    assert "2 results" in text
    assert "In Storage → In Transit" in text and "Hays / Tool Room / Locker" in text


def test_filters_are_passed_and_blanks_dropped(client, api):
    client.get("/movements?q=gun&item_type_id=1&building_id=&status=In+Use"
               "&date_from=2026-11-01&date_to=")
    assert api.called("search_movements") == [
        (1, {"q": "gun", "item_type_id": 1, "status": "In Use", "date_from": "2026-11-01"})]


def test_filters_stay_filled_in(client, api):
    html = client.get("/movements?item_type_id=1&date_from=2026-11-01").get_data(as_text=True)
    assert '<option value="1" selected>' in html
    assert 'value="2026-11-01"' in html


def test_no_results(client, api):
    api.returns["search_movements"] = []
    assert "No movements match." in page_text(client.get("/movements?q=zzz"))


def test_export_downloads_csv_with_same_filters(client, api):
    resp = client.get("/movements/export.csv?item_type_id=1&q=gun")
    assert resp.mimetype == "text/csv"
    assert "attachment" in resp.headers["Content-Disposition"]
    assert resp.get_data(as_text=True).startswith("date,item_name\n")
    assert api.called("export_movements_csv") == [(1, {"item_type_id": 1, "q": "gun"})]


def test_export_link_carries_current_filters(client, api):
    html = client.get("/movements?q=gun").get_data(as_text=True)
    assert "/movements/export.csv?q=gun" in html


def test_item_page_links_to_its_own_export(client, api):
    assert "/movements/export.csv?item_id=1" in client.get("/items/1").get_data(as_text=True)


def test_items_page_links_to_search(client, api):
    assert 'href="/movements"' in client.get("/items").get_data(as_text=True)
