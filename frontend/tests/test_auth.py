"""
Tests for db.register_owner() / db.verify_owner().
"""

import pytest
import db


def test_register_owner_creates_hashed_password_not_plaintext():
    owner_id = db.register_owner("Test", "User", "newuser@example.com", "correcthorse")
    assert owner_id is not None

    conn = db.get_connection()
    row = conn.execute(
        "SELECT password_hash FROM owners WHERE owner_id = ?", (owner_id,)
    ).fetchone()
    conn.close()

    assert row["password_hash"] != "correcthorse"
    assert row["password_hash"].startswith("scrypt:")


def test_register_owner_duplicate_email_raises():
    db.register_owner("First", "Person", "dupe@example.com", "password123")
    with pytest.raises(db.EmailAlreadyRegistered):
        db.register_owner("Second", "Person", "dupe@example.com", "different456")


def test_verify_owner_correct_password_succeeds():
    db.register_owner("Auth", "Test", "authtest@example.com", "mypassword")
    result = db.verify_owner("authtest@example.com", "mypassword")
    assert result is not None
    assert result["first_name"] == "Auth"
    assert "password_hash" not in result  # never leak the hash to the caller


def test_verify_owner_wrong_password_fails():
    db.register_owner("Wrong", "Pass", "wrongpass@example.com", "therealpassword")
    result = db.verify_owner("wrongpass@example.com", "notquiteright")
    assert result is None


def test_verify_owner_nonexistent_email_fails():
    result = db.verify_owner("doesnotexist@example.com", "whatever")
    assert result is None


def test_verify_owner_seeded_credentials_work():
    result = db.verify_owner("dale@prairieroofing.example", "roofing123")
    assert result is not None
    assert result["first_name"] == "Dale"
