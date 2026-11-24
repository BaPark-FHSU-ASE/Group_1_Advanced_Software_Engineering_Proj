import shutil
import sqlite3

import pytest

from app.config import Config
from tests.conftest import _REAL_DB
from tests.route_helpers import *  

app = load_app("stock_daddy_api_main_item_routes")


@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    path = tmp_path / "stockdaddy_item_routes.db"
    shutil.copyfile(_REAL_DB, path)
    monkeypatch.setattr(Config, "DB_PATH", str(path))
    return path


@pytest.fixture
def client(fresh_db):
    return app.test_client()


def test_retiring_an_item_keeps_its_history(client, fresh_db):
    movements_before = one_value(fresh_db, "SELECT COUNT(*) FROM item_movement")
    response = retire(client, "items", 1)
    assert response.status_code == 200
    assert response.get_json()["retired"] is not None
    assert one_value(fresh_db, "SELECT COUNT(*) FROM item_movement") == movements_before
    assert one_value(fresh_db, "SELECT COUNT(*) FROM item WHERE item_id = 1") == 1


def test_retiring_twice_just_returns_the_record(client):
    first = retire(client, "items", 1).get_json()
    second = retire(client, "items", 1)
    assert second.status_code == 200
    assert second.get_json()["retired"] == first["retired"]


def test_in_transit_item_can_still_be_retired_by_its_owner(client, fresh_db):
    storage = one_value(fresh_db, "SELECT storage_id FROM item WHERE item_id = 1")
    run_sql(fresh_db, "UPDATE item SET storage_id = NULL, item_status = 'In Transit' WHERE item_id = 1")
    run_sql(fresh_db, "INSERT INTO item_movement (item_id, from_storage_id) VALUES (1, ?)", (storage,))
    assert retire(client, "items", 1).status_code == 200


def test_employee_cannot_retire_an_item(client):
    assert_error(retire(client, "items", 1, user_id=JESS), 403, "owner role is required")


def test_owner_of_another_business_cannot_retire_this_item(client, fresh_db):
    boss = add_person(fresh_db, "boss@other.example")
    client.post("/businesses", json={"name": "Other Co", "owner_id": boss})
    assert_error(retire(client, "items", 1, user_id=boss), 404, "Item not found")
    assert one_value(fresh_db, "SELECT retired FROM item WHERE item_id = 1") is None


def test_retiring_a_missing_item_is_404(client):
    assert_error(retire(client, "items", 999999), 404, "Item not found")
    
    
def test_lists_hide_retired_items_unless_asked(client):
    everything = ids_of(client.get("/items?user_id=1"), "item_id")
    assert 1 in everything

    retire(client, "items", 1)
    after = ids_of(client.get("/items?user_id=1"), "item_id")
    assert 1 not in after
    assert len(after) == len(everything) - 1
    assert sorted(ids_of(client.get("/items?user_id=1&include_retired=true"), "item_id")) == sorted(everything)

def test_cannot_add_or_move_an_item_into_a_retired_storage_unit(client, fresh_db):
    storage_id = run_sql(
        fresh_db, "INSERT INTO storage (room_id, storage_type) VALUES (1, 'Closing Shelf')"
    )
    retire(client, "storages", storage_id)

    added = client.post(
        "/items", json={"user_id": DALE, "item_type_id": 1, "storage_id": storage_id}
    )
    assert_error(added, 409, "That storage unit is retired")

    moved = client.put(
        "/items/1",
        json={"user_id": DALE, "item_type_id": 1, "storage_id": storage_id, "item_status": "In Storage"},
    )
    assert_error(moved, 409, "That storage unit is retired")

def test_a_new_item_needs_a_storage_unit(client):
    response = client.post("/items", json={"user_id": DALE, "item_type_id": 1})
    assert_error(response, 400, "storage_id is required")


def _other_business_with_a_storage_unit(client, fresh_db):
    """A second business, owned by a new person, with one storage unit. -> (person, storage_id)"""
    person = add_person(fresh_db)
    business = client.post("/businesses", json={"name": "Other Co", "owner_id": person}).get_json()
    building = client.post(
        "/buildings",
        json={"user_id": person, "business_id": business["business_id"],
              "state": "KS", "city": "Salina", "street_address": "5 Elm St"},
    ).get_json()
    room = client.post(
        "/rooms",
        json={"user_id": person, "building_id": building["building_id"], "location": "Back"},
    ).get_json()
    unit = client.post(
        "/storages", json={"user_id": person, "room_id": room["room_id"], "storage_type": "Shelf"}
    ).get_json()
    return person, unit["storage_id"]


def _body_for(client, item_id, user_id, **changes):
    """A full PUT body that repeats the item as it is now, with `changes` applied."""
    item = client.get(f"/items/{item_id}?user_id={DALE}").get_json()
    body = {
        "user_id": user_id,
        "item_type_id": item["item_type_id"],
        "storage_id": item["storage_id"],
        "item_name": item["item_name"],
        "item_status": item["item_status"],
    }
    body.update(changes)
    return body


def test_members_see_their_businesses_items_including_ones_in_transit(client):
    for user in (DALE, JESS):
        response = client.get(f"/items?user_id={user}")
        assert response.status_code == 200
        assert len(response.get_json()) == 92
        assert 92 in ids_of(response, "item_id")  # item 92 is in transit, no storage unit


def test_a_stranger_sees_no_items_and_missing_user_id_is_400(client, fresh_db):
    stranger = add_person(fresh_db)
    assert client.get(f"/items?user_id={stranger}").get_json() == []
    assert_error(client.get("/items"), 400, "user_id is required")


def test_lists_only_show_items_of_your_own_businesses(client, fresh_db):
    person, storage_id = _other_business_with_a_storage_unit(client, fresh_db)
    item = client.post(
        "/items", json={"user_id": person, "item_type_id": 1, "storage_id": storage_id}
    ).get_json()
    assert ids_of(client.get(f"/items?user_id={person}"), "item_id") == [item["item_id"]]
    assert item["item_id"] not in ids_of(client.get(f"/items?user_id={DALE}"), "item_id")


def test_employee_can_view_an_item_but_a_stranger_cannot(client, fresh_db):
    assert client.get(f"/items/1?user_id={JESS}").status_code == 200
    stranger = add_person(fresh_db)
    not_yours = client.get(f"/items/1?user_id={stranger}")
    missing = client.get(f"/items/999999?user_id={stranger}")
    assert not_yours.status_code == missing.status_code == 404
    assert not_yours.get_json() == missing.get_json() == {"error": "Item not found"}
    assert_error(client.get("/items/1"), 400, "user_id is required")


def test_owner_and_employee_can_both_add_an_item(client):
    for user in (DALE, JESS):
        response = client.post(
            "/items",
            json={"user_id": user, "item_type_id": 1, "storage_id": 1, "item_name": "New Drill"},
        )
        assert response.status_code == 201
        assert response.get_json()["item_status"] == "In Storage"


def test_stranger_cannot_add_an_item_to_someone_elses_storage_unit(client, fresh_db):
    stranger = add_person(fresh_db)
    response = client.post(
        "/items", json={"user_id": stranger, "item_type_id": 1, "storage_id": 1}
    )
    assert_error(response, 404, "Storage not found")


def test_employee_can_change_an_items_status(client):
    new_status = "In Use" if client.get(f"/items/1?user_id={JESS}").get_json()["item_status"] != "In Use" else "In Storage"
    response = client.put("/items/1", json=_body_for(client, 1, JESS, item_status=new_status))
    assert response.status_code == 200
    assert response.get_json()["item_status"] == new_status

    in_transit = client.put("/items/1", json=_body_for(client, 1, JESS, item_status="In Transit"))
    assert in_transit.status_code == 200
    assert in_transit.get_json()["storage_id"] is not None


def test_employee_can_move_an_item_to_another_storage_unit(client):
    response = client.put("/items/1", json=_body_for(client, 1, JESS, storage_id=2))
    assert response.status_code == 200
    assert response.get_json()["storage_id"] == 2


def test_employee_cannot_rename_or_retype_an_item(client):
    renamed = client.put("/items/1", json=_body_for(client, 1, JESS, item_name="Renamed"))
    assert_error(renamed, 403, "owner role is required")

    retyped = client.put("/items/1", json=_body_for(client, 1, JESS, item_type_id=2))
    assert_error(retyped, 403, "owner role is required")

def test_owner_can_rename_and_move_an_item(client):
    response = client.put(
        "/items/1", json=_body_for(client, 1, DALE, item_name="Renamed", storage_id=2)
    )
    assert response.status_code == 200
    assert response.get_json()["item_name"] == "Renamed"
    assert response.get_json()["storage_id"] == 2


def test_cannot_move_an_item_into_a_storage_unit_you_are_not_in(client, fresh_db):
    _, other_storage = _other_business_with_a_storage_unit(client, fresh_db)
    before = one_value(fresh_db, "SELECT storage_id FROM item WHERE item_id = 1")
    response = client.put("/items/1", json=_body_for(client, 1, DALE, storage_id=other_storage))
    assert_error(response, 404, "Storage not found")
    assert one_value(fresh_db, "SELECT storage_id FROM item WHERE item_id = 1") == before


def test_editing_a_missing_item_or_someone_elses_item_is_404(client, fresh_db):
    stranger = add_person(fresh_db)
    body = {"user_id": stranger, "item_type_id": 1, "storage_id": 1, "item_status": "In Use"}
    assert_error(client.put("/items/1", json=body), 404, "Item not found")
    assert_error(client.put("/items/999999", json=dict(body, user_id=DALE)), 404, "Item not found")


def test_owner_can_delete_an_item_with_no_history(client):
    item = client.post(
        "/items", json={"user_id": DALE, "item_type_id": 1, "storage_id": 1}
    ).get_json()
    assert client.delete(f"/items/{item['item_id']}?user_id={DALE}").status_code == 204
    assert client.get(f"/items/{item['item_id']}?user_id={DALE}").status_code == 404


def test_employee_and_stranger_cannot_delete_an_item(client, fresh_db):
    item = client.post(
        "/items", json={"user_id": DALE, "item_type_id": 1, "storage_id": 1}
    ).get_json()
    item_id = item["item_id"]
    assert_error(client.delete(f"/items/{item_id}?user_id={JESS}"), 403, "owner role is required")
    stranger = add_person(fresh_db)
    assert_error(client.delete(f"/items/{item_id}?user_id={stranger}"), 404, "Item not found")
    assert_error(client.delete(f"/items/{item_id}"), 400, "user_id is required")
    assert client.get(f"/items/{item_id}?user_id={DALE}").status_code == 200



def _bulk(client, **changes):
    body = {"user_id": DALE, "storage_id": 1, "item_type_id": 1, "quantity": 1}
    body.update(changes)
    return client.post("/items/bulk", json=body)


def _item_count(path):
    return one_value(path, "SELECT COUNT(*) FROM item")


def _names(path, item_ids):
    return [one_value(path, "SELECT item_name FROM item WHERE item_id = ?", (i,)) for i in item_ids]


def test_bulk_add_makes_the_items_and_one_movement_row_each(client, fresh_db):
    items_before = _item_count(fresh_db)
    movements_before = one_value(fresh_db, "SELECT COUNT(*) FROM item_movement")

    response = _bulk(client, quantity=3)
    assert response.status_code == 201
    item_ids = response.get_json()["item_ids"]
    assert len(item_ids) == len(set(item_ids)) == 3

    assert _item_count(fresh_db) == items_before + 3
    assert one_value(fresh_db, "SELECT COUNT(*) FROM item_movement") == movements_before + 3
    for item_id in item_ids:
        item = client.get(f"/items/{item_id}?user_id={DALE}").get_json()
        assert (item["item_type_id"], item["storage_id"], item["item_status"]) == (1, 1, "In Storage")
        movement = one_value(
            fresh_db,
            "SELECT COUNT(*) FROM item_movement WHERE item_id = ? "
            "AND from_storage_id IS NULL AND to_storage_id = 1",
            (item_id,),
        )
        assert movement == 1


def test_bulk_add_names_items_after_their_type_and_keeps_counting(client, fresh_db):
    already = one_value(fresh_db, "SELECT COUNT(*) FROM item WHERE item_type_id = 1")
    first = _bulk(client, quantity=2).get_json()["item_ids"]
    second = _bulk(client, quantity=1).get_json()["item_ids"]
    assert _names(fresh_db, first) == [f"Nail Gun #{already + 1}", f"Nail Gun #{already + 2}"]
    assert _names(fresh_db, second) == [f"Nail Gun #{already + 3}"]


def test_bulk_add_uses_a_typed_name_as_it_is_for_one_item_and_numbers_it_for_several(client, fresh_db):
    one = _bulk(client, item_name="  Big Red  ").get_json()["item_ids"]
    several = _bulk(client, item_name="Big Red", quantity=3).get_json()["item_ids"]
    assert _names(fresh_db, one) == ["Big Red"]
    assert _names(fresh_db, several) == ["Big Red #1", "Big Red #2", "Big Red #3"]


def test_bulk_add_treats_a_blank_name_like_no_name(client, fresh_db):
    already = one_value(fresh_db, "SELECT COUNT(*) FROM item WHERE item_type_id = 1")
    ids = _bulk(client, item_name="   ").get_json()["item_ids"]
    assert _names(fresh_db, ids) == [f"Nail Gun #{already + 1}"]


def test_bulk_add_counts_retired_items_when_numbering(client, fresh_db):
    run_sql(fresh_db, "UPDATE item SET retired = CURRENT_TIMESTAMP WHERE item_type_id = 1")
    already = one_value(fresh_db, "SELECT COUNT(*) FROM item WHERE item_type_id = 1")
    ids = _bulk(client).get_json()["item_ids"]
    assert _names(fresh_db, ids) == [f"Nail Gun #{already + 1}"]


def test_an_employee_can_add_items_too(client):
    assert _bulk(client, user_id=JESS, quantity=2).status_code == 201


def test_bulk_add_shows_up_in_the_item_list(client):
    before = len(client.get(f"/items?user_id={DALE}").get_json())
    ids = _bulk(client, quantity=4).get_json()["item_ids"]
    listed = ids_of(client.get(f"/items?user_id={DALE}"), "item_id")
    assert len(listed) == before + 4
    assert set(ids) <= set(listed)


def test_bulk_add_accepts_exactly_the_limits(client, fresh_db):
    before = _item_count(fresh_db)
    assert _bulk(client, quantity=1).status_code == 201
    assert _bulk(client, quantity=100).status_code == 201
    assert _item_count(fresh_db) == before + 101


def test_bulk_add_refuses_a_quantity_outside_one_to_a_hundred(client, fresh_db):
    before = _item_count(fresh_db)
    for quantity in (0, -1, 101, 5000):
        assert_error(_bulk(client, quantity=quantity), 400, "Quantity must be between 1 and 100.")
    assert_error(_bulk(client, quantity="3"), 400, "quantity must be a whole number")
    assert_error(_bulk(client, quantity=2.5), 400, "quantity must be a whole number")
    assert_error(client.post("/items/bulk", json={"user_id": DALE, "storage_id": 1, "item_type_id": 1}),
                 400, "quantity is required")
    assert _item_count(fresh_db) == before


def test_bulk_add_refuses_a_name_that_would_be_too_long(client, fresh_db):
    before = _item_count(fresh_db)
    assert _bulk(client, item_name="x" * 100).status_code == 201
    assert_error(_bulk(client, item_name="x" * 101), 400, "Item name must be 100 characters or fewer.")
    # 98 characters is fine alone, but " #10" makes the tenth name 102 long.
    assert_error(_bulk(client, item_name="x" * 98, quantity=10), 400, "Item name must be 100 characters or fewer.")
    assert _item_count(fresh_db) == before + 1


def test_bulk_add_checks_who_you_are_and_what_exists(client, fresh_db):
    stranger = add_person(fresh_db)
    before = _item_count(fresh_db)
    assert_error(_bulk(client, user_id=stranger), 404, "Storage not found")
    assert_error(_bulk(client, storage_id=999999), 404, "Storage not found")
    assert_error(_bulk(client, item_type_id=999999), 404, "Item type not found")
    assert _item_count(fresh_db) == before


def test_bulk_add_cannot_use_another_business_storage_unit(client, fresh_db):
    person, their_storage = _other_business_with_a_storage_unit(client, fresh_db)
    before = _item_count(fresh_db)
    assert_error(_bulk(client, storage_id=their_storage), 404, "Storage not found")
    assert _bulk(client, user_id=person, storage_id=their_storage).status_code == 201
    assert _item_count(fresh_db) == before + 1


def test_bulk_add_refuses_a_retired_storage_unit(client, fresh_db):
    storage_id = run_sql(fresh_db, "INSERT INTO storage (room_id, storage_type) VALUES (1, 'Closing Shelf')")
    retire(client, "storages", storage_id)
    before = _item_count(fresh_db)
    assert_error(_bulk(client, storage_id=storage_id), 409, "That storage unit is retired")
    assert _item_count(fresh_db) == before




def _set_status(client, item_id, status, user_id=DALE, **extra):
    body = {"user_id": user_id, "status": status}
    body.update(extra)
    return client.post(f"/items/{item_id}/status", json=body)


def _item_row(path, item_id):
    conn = sqlite3.connect(path)
    row = conn.execute("SELECT item_status, storage_id FROM item WHERE item_id = ?", (item_id,)).fetchone()
    conn.close()
    return row


def _movements(path, item_id):
    conn = sqlite3.connect(path)
    rows = conn.execute(
        "SELECT from_storage_id, to_storage_id, from_status, to_status FROM item_movement "
        "WHERE item_id = ? ORDER BY item_movement_id", (item_id,)
    ).fetchall()
    conn.close()
    return rows


def test_in_storage_and_in_use_swap_in_place_and_log_only_the_status(client, fresh_db):
    before = _movements(fresh_db, 1)

    response = _set_status(client, 1, "In Use")
    assert response.status_code == 200
    assert response.get_json() == {"changed": True}
    assert _item_row(fresh_db, 1) == ("In Use", 1)

    assert _set_status(client, 1, "In Storage").get_json() == {"changed": True}
    assert _item_row(fresh_db, 1) == ("In Storage", 1)
    assert _movements(fresh_db, 1)[len(before):] == [
        (None, None, "In Storage", "In Use"),
        (None, None, "In Use", "In Storage"),
    ]


def test_an_employee_can_change_status(client, fresh_db):
    assert _set_status(client, 1, "In Use", user_id=JESS).get_json() == {"changed": True}
    assert _item_row(fresh_db, 1)[0] == "In Use"


def test_going_in_transit_empties_the_storage_unit_and_logs_where_it_left_from(client, fresh_db):
    response = _set_status(client, 1, "In Transit")
    assert response.get_json() == {"changed": True}
    assert _item_row(fresh_db, 1) == ("In Transit", None)
    assert _movements(fresh_db, 1)[-1] == (1, None, "In Storage", "In Transit")


def test_an_item_in_transit_stays_on_its_businesses_lists(client, fresh_db):
    _set_status(client, 1, "In Transit")
    assert 1 in ids_of(client.get(f"/items?user_id={DALE}"), "item_id")
    assert client.get(f"/items/1?user_id={JESS}").status_code == 200
    stranger = add_person(fresh_db)
    assert 1 not in ids_of(client.get(f"/items?user_id={stranger}"), "item_id")


def test_arriving_needs_a_storage_unit_and_puts_the_item_there(client, fresh_db):
    before = _movements(fresh_db, 92)
    for extra in ({}, {"storage_id": 0}):
        assert_error(_set_status(client, 92, "In Storage", **extra), 400, "Choose where the item arrived.")
    assert _item_row(fresh_db, 92) == ("In Transit", None)
    assert _movements(fresh_db, 92) == before

    response = _set_status(client, 92, "In Use", storage_id=2)
    assert response.get_json() == {"changed": True}
    assert _item_row(fresh_db, 92) == ("In Use", 2)
    assert _movements(fresh_db, 92)[-1] == (None, 2, "In Transit", "In Use")


def test_the_whole_trip_out_and_back(client, fresh_db):
    _set_status(client, 1, "In Transit")
    _set_status(client, 1, "In Storage", storage_id=3)
    assert _item_row(fresh_db, 1) == ("In Storage", 3)
    assert _movements(fresh_db, 1)[-2:] == [
        (1, None, "In Storage", "In Transit"),
        (None, 3, "In Transit", "In Storage"),
    ]


def test_asking_for_the_status_it_already_has_changes_nothing(client, fresh_db):
    before = _movements(fresh_db, 1)
    response = _set_status(client, 1, "In Storage")
    assert response.status_code == 200
    assert response.get_json() == {"changed": False}
    assert _movements(fresh_db, 1) == before
    # An item already in transit doesn't need a destination to stay there.
    assert _set_status(client, 92, "In Transit").get_json() == {"changed": False}


def test_a_storage_unit_is_ignored_unless_the_item_is_arriving(client, fresh_db):
    _set_status(client, 1, "In Use", storage_id=2)
    assert _item_row(fresh_db, 1) == ("In Use", 1)


def test_status_must_be_one_of_the_three(client, fresh_db):
    sentence = "Status must be In Storage, In Use or In Transit."
    for status in ("Broken", "in use", ""):
        assert_error(_set_status(client, 1, status), 400, sentence)
    assert_error(client.post("/items/1/status", json={"user_id": DALE}), 400, sentence)
    assert _item_row(fresh_db, 1) == ("In Storage", 1)


def test_status_needs_a_json_object_and_a_user(client):
    assert_error(client.post("/items/1/status", data="hello"), 400, "Request body must be a JSON object")
    assert_error(client.post("/items/1/status", json={"status": "In Use"}), 400, "user_id is required")


def test_a_stranger_or_a_missing_item_is_404_and_nothing_changes(client, fresh_db):
    stranger = add_person(fresh_db)
    before = _movements(fresh_db, 1)
    assert_error(_set_status(client, 1, "In Use", user_id=stranger), 404, "Item not found")
    assert_error(_set_status(client, 999999, "In Use"), 404, "Item not found")
    assert _item_row(fresh_db, 1) == ("In Storage", 1)
    assert _movements(fresh_db, 1) == before


def test_arriving_needs_access_to_the_storage_unit_and_it_cannot_be_retired(client, fresh_db):
    _, their_storage = _other_business_with_a_storage_unit(client, fresh_db)
    assert_error(_set_status(client, 92, "In Storage", storage_id=their_storage), 404, "Storage not found")
    assert_error(_set_status(client, 92, "In Storage", storage_id=999999), 404, "Storage not found")

    closing = run_sql(fresh_db, "INSERT INTO storage (room_id, storage_type) VALUES (1, 'Closing Shelf')")
    retire(client, "storages", closing)
    assert_error(_set_status(client, 92, "In Storage", storage_id=closing), 409, "That storage unit is retired")
    assert _item_row(fresh_db, 92) == ("In Transit", None)


def test_a_retired_item_cannot_change_status(client, fresh_db):
    retire(client, "items", 1)
    before = _movements(fresh_db, 1)
    assert_error(_set_status(client, 1, "In Use"), 409, "That item is retired")
    assert _item_row(fresh_db, 1) == ("In Storage", 1)
    assert _movements(fresh_db, 1) == before