import importlib.util
import shutil
from pathlib import Path
 
import pytest
 
from app.config import Config
from tests.conftest import _REAL_DB
 
_spec = importlib.util.spec_from_file_location(
    "stock_daddy_api_main_errors", Path(__file__).resolve().parent.parent / "app.py"
)
_main = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_main)
 
GOOD_BUILDING = {"user_id": 1, "business_id": 1, "state": "KS", "city": "Hays", "street_address": "1 Main St"}
 
 
@pytest.fixture
def client(monkeypatch, tmp_path):
    path = tmp_path / "stockdaddy_errors.db"
    shutil.copyfile(_REAL_DB, path)
    monkeypatch.setattr(Config, "DB_PATH", str(path))
    return _main.app.test_client()
 
 
def assert_error(response, status, text):
    assert response.status_code == status
    assert response.is_json
    assert text in response.get_json()["error"]
 
 
def assert_next_write_works(client):
    """The proof the database is not left locked after a refused write."""
    assert client.post("/buildings", json=GOOD_BUILDING).status_code == 201
 
 
# ---- bad input -> 400 -
 
def test_post_missing_field_is_400(client):
    body = {k: v for k, v in GOOD_BUILDING.items() if k != "state"}
    assert_error(client.post("/buildings", json=body), 400, "state is required")
 
 
def test_put_missing_field_is_400(client):
    assert_error(client.put("/buildings/1", json={"city": "Hays"}), 400, "business_id is required")
 
 
def test_body_that_is_not_json_is_400(client):
    assert_error(client.post("/buildings", data="hello"), 400, "JSON object")
 
 
def test_body_that_is_a_list_is_400(client):
    assert_error(client.post("/buildings", json=[1, 2]), 400, "JSON object")
 
 
def test_wrong_type_is_400(client):
    body = dict(GOOD_BUILDING, business_id="1")
    assert_error(client.post("/buildings", json=body), 400, "business_id must be a whole number")
 
def test_every_create_route_rejects_an_empty_body(client):
    for path in ("/auth/register", "/businesses", "/buildings", "/rooms", "/storages",
                 "/item_types", "/items", "/items/bulk"):
        response = client.post(path, json={})
        assert response.status_code == 400, path
        assert "is required" in response.get_json()["error"], path
 
 
def test_item_rejects_text_storage_id(client):
    body = {"item_type_id": 1, "storage_id": "abc"}
    assert_error(client.post("/items", json=body), 400, "storage_id must be a whole number")
 
 
def test_unknown_parent_is_409_and_next_write_works(client):
    body = {"user_id": 1, "item_type_id": 999999, "storage_id": 1}
    assert_error(client.post("/items", json=body), 409, "doesn't exist")
    assert_next_write_works(client)
 
def test_duplicate_email_is_409_and_next_write_works(client):
    # Jess changing her email to Dale's runs into the UNIQUE rule on owners.email.
    body = {"user_id": 2, "first_name": "Jess", "last_name": "Crew", "email": "dale@prairieroofing.example"}
    assert_error(client.put("/owners/2", json=body), 409, "email already exists")
    assert_next_write_works(client)
 
def test_disallowed_status_is_400_and_next_write_works(client):
    body = {"user_id": 1, "item_type_id": 1, "storage_id": 1, "item_status": "Lost"}
    assert_error(client.post("/items", json=body), 400, "chk_item_status")
    assert_next_write_works(client)
    
def test_zero_replacement_cost_is_400_and_next_write_works(client):
    body = {"user_id": 1, "name": "Brand New Thing", "replacement_cost": 0}
    assert_error(client.post("/item_types", json=body), 400, "not allowed")
    assert_next_write_works(client)
 
def test_deleting_a_building_in_use_is_409_and_next_write_works(client):
    assert_error(client.delete("/buildings/1?user_id=1"), 409, "still depend")
    assert_next_write_works(client)
 
def test_good_post_still_works(client):
    response = client.post("/buildings", json=GOOD_BUILDING)
    assert response.status_code == 201
    assert response.get_json()["city"] == "Hays"
 
def test_item_defaults_status_when_not_sent(client):
    response = client.post("/items", json={"user_id": 1, "item_type_id": 1, "storage_id": 1})
    assert response.status_code == 201
    assert response.get_json()["item_status"] == "In Storage"
 
 
def test_item_type_accepts_optional_fields(client):
    body = {"user_id": 1, "name": "Ladder Strap", "description": "Heavy duty", "replacement_cost": 12.5}
    response = client.post("/item_types", json=body)
    assert response.status_code == 201
    assert response.get_json()["replacement_cost"] == 12.5