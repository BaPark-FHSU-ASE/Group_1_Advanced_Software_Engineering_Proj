import importlib.util
import sqlite3
from pathlib import Path

DALE, JESS = 1, 2


def load_app(module_name):
    """Load stock_daddy_api/app.py (it sits next to the app/ package) by path."""
    spec = importlib.util.spec_from_file_location(
        module_name, Path(__file__).resolve().parent.parent / "app.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.app


def run_sql(path, sql, params=()):
    """Run one statement straight against the test database; returns the new row id."""
    conn = sqlite3.connect(path)
    cursor = conn.execute(sql, params)
    conn.commit()
    conn.close()
    return cursor.lastrowid


def one_value(path, sql, params=()):
    conn = sqlite3.connect(path)
    value = conn.execute(sql, params).fetchone()[0]
    conn.close()
    return value


def first_column(path, sql, params=()):
    conn = sqlite3.connect(path)
    values = [row[0] for row in conn.execute(sql, params)]
    conn.close()
    return values


def add_person(path, email="someone@example.com"):
    return run_sql(
        path,
        "INSERT INTO owners (first_name, last_name, email, password_hash) "
        "VALUES ('Some', 'One', ?, 'x')",
        (email,),
    )


def add_empty_building(path):
    return run_sql(
        path,
        "INSERT INTO building (business_id, state, city, street_address) "
        "VALUES (1, 'KS', 'Hays', '1 Empty St')",
    )


def retire(client, word, record_id, user_id=DALE):
    """POST /<word>/<id>/retire, e.g. retire(client, "rooms", 1)."""
    return client.post(f"/{word}/{record_id}/retire", json={"user_id": user_id})


def assert_error(response, status, text):
    assert response.status_code == status
    assert text in response.get_json()["error"]
    
    


def ids_of(response, key):
    return [row[key] for row in response.get_json()]    