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
    
def test_get_by_email_finds_a_person_whatever_the_letter_case():
    found = owner_repository.get_by_email("dale@prairieroofing.example")
    assert found.owner_id == 1
    assert owner_repository.get_by_email("DALE@PrairieRoofing.example").owner_id == 1


def test_get_by_email_returns_none_for_an_unknown_email():
    assert owner_repository.get_by_email("nobody@nowhere.example") is None    