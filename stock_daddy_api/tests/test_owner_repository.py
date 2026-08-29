from app.repositories import owner_repository


def test_get_all_returns_list_of_owners():
    owners = owner_repository.get_all()

    assert isinstance(owners, list)
    assert len(owners) >= 1


def test_get_all_returns_seeded_owner():
    owners = owner_repository.get_all()

    dale = owners[0]
    assert dale.first_name == "Dale"
    assert dale.last_name == "Renner"
    assert dale.email == "dale@prairieroofing.example"