from app.models.owner import Owner


def test_owner_init_sets_all_fields():
    owner = Owner(
        owner_id=1,
        first_name="Dale",
        last_name="Renner",
        email="dale@prairieroofing.example",
        password_hash="somehash", # to-do, modify later
        date_added="2026-01-01 00:00:00",
    )

    assert owner.owner_id == 1
    assert owner.first_name == "Dale"
    assert owner.last_name == "Renner"
    assert owner.email == "dale@prairieroofing.example"
    assert owner.password_hash == "somehash"
    assert owner.date_added == "2026-01-01 00:00:00"