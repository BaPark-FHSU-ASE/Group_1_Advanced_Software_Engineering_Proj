
import csv
import io
import shutil

import pytest

from app.config import Config
from tests.conftest import _REAL_DB
from tests.route_helpers import *  # noqa: F403  (DALE, JESS, load_app, run_sql, ...)

app = load_app("stock_daddy_api_main_item_movement_routes")

COLUMNS = {"movement_id", "date", "item_id", "item_name", "item_type", "building", "from", "to", "status_change"}


@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    path = tmp_path / "stockdaddy_item_movement_routes.db"
    shutil.copyfile(_REAL_DB, path)
    monkeypatch.setattr(Config, "DB_PATH", str(path))
    return path


@pytest.fixture
def client(fresh_db):
    return app.test_client()


def _rows(client, user_id=DALE, **filters):
    query = "&".join(f"{key}={value}" for key, value in dict(user_id=user_id, **filters).items())
    response = client.get(f"/movements?{query}")
    assert response.status_code == 200, response.get_json()
    return response.get_json()


def _status(client, item_id, status, user_id=DALE, **extra):
    body = {"user_id": user_id, "status": status}
    body.update(extra)
    response = client.post(f"/items/{item_id}/status", json=body)
    assert response.status_code == 200, response.get_json()


def _add_items(client, user_id=DALE, **body):
    base = {"user_id": user_id, "storage_id": 1, "item_type_id": 1, "quantity": 1}
    base.update(body)
    response = client.post("/items/bulk", json=base)
    assert response.status_code == 201, response.get_json()
    return response.get_json()["item_ids"]


def _other_business_with_a_storage_unit(client, fresh_db):
    person = add_person(fresh_db, "boss@other.example")
    business = client.post("/businesses", json={"name": "Other Co", "owner_id": person}).get_json()
    building = client.post("/buildings", json={
        "user_id": person, "business_id": business["business_id"],
        "state": "KS", "city": "Wichita", "street_address": "5 Elm St"}).get_json()
    room = client.post("/rooms", json={"user_id": person, "building_id": building["building_id"], "location": "Back"}).get_json()
    unit = client.post("/storages", json={"user_id": person, "room_id": room["room_id"], "storage_type": "Shelf"}).get_json()
    return person, unit["storage_id"]



def test_members_see_every_movement_newest_first_in_the_contract_shape(client):
    for user in (DALE, JESS):
        rows = _rows(client, user)
        assert len(rows) == 94
        assert all(set(row) == COLUMNS for row in rows)
        assert [row["date"] for row in rows] == sorted((row["date"] for row in rows), reverse=True)

    by_id = {row["movement_id"]: row for row in _rows(client)}
    assert by_id[93] == {
        "movement_id": 93, "date": "2026-11-03", "item_id": 92, "item_name": "Air Compressor #99",
        "item_type": "Air Compressor", "building": "Salina",
        "from": "Salina / Salina North main storage / Locker", "to": "—", "status_change": None,
    }
    assert by_id[94]["status_change"] == "In Storage → In Use"
    assert (by_id[94]["item_id"], by_id[94]["building"], by_id[94]["from"], by_id[94]["to"]) == (4, "Salina", "—", "—")


def test_a_stranger_sees_nothing_and_the_user_id_is_required(client, fresh_db):
    assert _rows(client, add_person(fresh_db)) == []
    assert_error(client.get("/movements"), 400, "user_id is required")
    assert_error(client.get("/movements?user_id=abc"), 400, "user_id must be a whole number")


def test_each_business_sees_only_its_own_history(client, fresh_db):
    boss, storage = _other_business_with_a_storage_unit(client, fresh_db)
    _add_items(client, user_id=boss, storage_id=storage, quantity=2)
    theirs = _rows(client, boss)
    assert len(theirs) == 2
    assert all(row["building"] == "Wichita" and row["to"] == "Wichita / Back / Shelf" for row in theirs)
    assert len(_rows(client, DALE)) == 94


def test_new_items_and_status_changes_show_up_with_their_places(client):
    new_ids = _add_items(client, quantity=2, item_name="Fresh Gun")
    added = _rows(client, item_id=new_ids[0])
    assert len(added) == 1
    assert (added[0]["from"], added[0]["to"], added[0]["status_change"]) == (
        "—", "Salina / Salina North main storage / Locker", None)

    _status(client, 1, "In Use")
    _status(client, 1, "In Transit")
    _status(client, 1, "In Storage", storage_id=6)
    history = _rows(client, item_id=1)           # newest first
    assert [row["status_change"] for row in history[:3]] == [
        "In Transit → In Storage", "In Use → In Transit", "In Storage → In Use"]
    assert history[0]["from"] == "—" and history[0]["to"] == "Abilene / Abilene main storage / Closet"
    assert history[1]["from"].startswith("Salina / ") and history[1]["to"] == "—"
    assert (history[2]["from"], history[2]["to"], history[2]["building"]) == ("—", "—", "Salina")


def test_an_item_in_transit_keeps_its_history_on_the_list(client):
    _status(client, 1, "In Transit")
    rows = _rows(client, item_id=1)
    assert rows[0]["status_change"] == "In Storage → In Transit"
    assert _rows(client, JESS, item_id=1) == rows


def test_a_status_change_is_filed_under_the_building_the_item_was_in_at_the_time(client):
    _status(client, 1, "In Transit")
    _status(client, 1, "In Storage", storage_id=6)      # now in Abilene (storage unit 6)
    _status(client, 1, "In Use")                        # a status-only row, in Abilene
    newest = _rows(client, item_id=1)[0]
    assert (newest["status_change"], newest["building"], newest["from"], newest["to"]) == (
        "In Storage → In Use", "Abilene", "—", "—")


def test_a_retired_items_movements_are_left_out(client):
    before = len(_rows(client))
    own = len(_rows(client, item_id=1))
    assert own >= 1
    retire(client, "items", 1)
    assert len(_rows(client)) == before - own
    assert _rows(client, item_id=1) == []



def test_item_and_item_type_filters(client, fresh_db):
    assert {row["item_id"] for row in _rows(client, item_id=92)} == {92}
    assert _rows(client, item_id=999999) == []
    expected = one_value(
        fresh_db, "SELECT COUNT(*) FROM item_movement m JOIN item i ON i.item_id = m.item_id WHERE i.item_type_id = 1")
    nail_guns = _rows(client, item_type_id=1)
    assert len(nail_guns) == expected
    assert {row["item_type"] for row in nail_guns} == {"Nail Gun"}


def test_building_filter_takes_departures_arrivals_and_status_changes_in_that_building(client, fresh_db):
    _status(client, 1, "In Transit")
    _status(client, 1, "In Storage", storage_id=6)
    in_abilene = _rows(client, building_id=3)
    assert len(in_abilene) == one_value(
        fresh_db,
        "SELECT COUNT(DISTINCT m.item_movement_id) FROM item_movement m JOIN storage s "
        "ON s.storage_id IN (m.from_storage_id, m.to_storage_id) JOIN room r ON r.room_id = s.room_id "
        "WHERE r.building_id = 3",
    )
    assert in_abilene[0]["status_change"] == "In Transit → In Storage"      # the arrival
    assert all("Abilene" in (row["from"] + row["to"] + row["building"]) for row in in_abilene)
    # item 1 leaving Salina is filed under Salina, not Abilene
    assert "In Storage → In Transit" not in [row["status_change"] for row in in_abilene]
    assert "In Storage → In Transit" in [row["status_change"] for row in _rows(client, building_id=1)]


def test_status_filter_matches_the_status_before_or_after_a_change(client):
    assert _rows(client, status="In Transit".replace(" ", "%20")) == []
    _status(client, 1, "In Use")
    _status(client, 1, "In Storage")
    changes = [row["status_change"] for row in _rows(client, status="In%20Use")]
    assert sorted(changes) == sorted(["In Storage → In Use", "In Use → In Storage", "In Storage → In Use"])


def test_date_filters_include_both_days(client, fresh_db):
    on_the_third = one_value(fresh_db, "SELECT COUNT(*) FROM item_movement WHERE date(moved_at) = '2026-11-03'")
    assert on_the_third > 0
    assert len(_rows(client, date_from="2026-11-03", date_to="2026-11-03")) == on_the_third
    assert {row["date"] for row in _rows(client, date_from="2026-11-01")} == {"2026-11-01", "2026-11-03"}
    assert {row["date"] for row in _rows(client, date_to="2026-10-13")} == {"2026-10-13"}
    assert _rows(client, date_from="2027-01-01") == []


def test_name_search_ignores_capitals_and_takes_percent_signs_literally(client, fresh_db):
    expected = one_value(fresh_db, "SELECT COUNT(*) FROM item_movement m JOIN item i ON i.item_id = m.item_id WHERE i.item_name LIKE '%nail gun #1%'")
    assert len(_rows(client, q="NAIL%20GUN%20%231")) == expected > 0
    assert _rows(client, q="%25") == []
    _add_items(client, item_name="100% Cotton Glove")
    assert [row["item_name"] for row in _rows(client, q="100%25")] == ["100% Cotton Glove"]
    assert [row["item_name"] for row in _rows(client, q="_otton")] == []


def test_filters_work_together_and_blank_ones_are_ignored(client):
    both = _rows(client, item_type_id=1, q="%231")
    assert both and all(row["item_type"] == "Nail Gun" and "#1" in row["item_name"] for row in both)
    assert len(_rows(client, item_id="", status="", q="", date_from="")) == 94


def test_bad_filters_get_plain_sentences(client):
    assert_error(client.get(f"/movements?user_id={DALE}&status=Broken"), 400, "Status must be In Storage, In Use or In Transit.")
    assert_error(client.get(f"/movements?user_id={DALE}&date_from=11/03/2026"), 400, "Dates must look like 2026-11-24 (year-month-day).")
    assert_error(client.get(f"/movements?user_id={DALE}&date_to=2026-13-01"), 400, "Dates must look like 2026-11-24")
    assert_error(client.get(f"/movements?user_id={DALE}&date_from=2026-12-01&date_to=2026-11-01"), 400, "The start date can't be after the end date.")
    assert_error(client.get(f"/movements?user_id={DALE}&item_id=abc"), 400, "item_id must be a whole number")
    assert_error(client.get(f"/movements?user_id={DALE}&building_id=1.5"), 400, "building_id must be a whole number")



def _csv(client, user_id=DALE, **filters):
    query = "&".join(f"{key}={value}" for key, value in dict(user_id=user_id, **filters).items())
    response = client.get(f"/movements/export?{query}")
    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    return list(csv.reader(io.StringIO(response.get_data(as_text=True))))


def test_the_export_has_a_header_row_and_the_same_rows_as_the_list(client):
    table = _csv(client)
    assert table[0] == ["movement_id", "date", "item_id", "item_name", "item_type", "building", "from", "to", "status_change"]
    listed = _rows(client)
    assert len(table) == 1 + len(listed)
    first, row = table[1], listed[0]
    assert first == [str(row["movement_id"]), row["date"], str(row["item_id"]), row["item_name"],
                     row["item_type"], row["building"], row["from"], row["to"], row["status_change"] or ""]


def test_the_export_takes_the_same_filters_and_the_same_checks(client, fresh_db):
    assert len(_csv(client, item_id=92)) == 2
    assert len(_csv(client, date_from="2026-11-01", status="In%20Use")) == 2
    assert _csv(client, add_person(fresh_db)) == [_csv(client)[0]]
    assert_error(client.get("/movements/export"), 400, "user_id is required")
    assert_error(client.get(f"/movements/export?user_id={DALE}&status=Broken"), 400, "Status must be")


def test_the_export_quotes_commas_and_defuses_spreadsheet_formulas(client):
    _add_items(client, item_name='Gun, "big"')
    _add_items(client, item_name="=SUM(A1:A9)")
    _add_items(client, item_name="@home")
    names = {row[3] for row in _csv(client)[1:]}
    assert 'Gun, "big"' in names
    assert "'=SUM(A1:A9)" in names and "'@home" in names
    assert "=SUM(A1:A9)" not in names
    # The list itself keeps the real names.
    assert "=SUM(A1:A9)" in {row["item_name"] for row in _rows(client)}
