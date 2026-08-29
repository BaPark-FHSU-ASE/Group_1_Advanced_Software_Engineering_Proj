
class Owner:
    def __init__(self, owner_id, first_name, last_name, email, password_hash, date_added=None):
        self.owner_id = owner_id
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.password_hash = password_hash
        self.date_added = date_added