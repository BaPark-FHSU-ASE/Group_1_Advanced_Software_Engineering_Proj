
class Owner:
    def __init__(self, owner_id, first_name, last_name, email, password_hash, date_added=None):
        self.owner_id = owner_id
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.password_hash = password_hash
        self.date_added = date_added

        # From row methods will be used to instantiate objects from each returned row from the repository layer. 
    @classmethod
    def from_row(cls, row):
        """Build an Owner from a sqlite3.Row returned by a query."""
        return cls(
            owner_id=row["owner_id"],
            first_name=row["first_name"],
            last_name=row["last_name"],
            email=row["email"],
            password_hash=row["password_hash"],
            date_added=row["date_added"],
        )     
    
    def to_dict(self):
        """Convert to a plain dict, safe to return as JSON. Excludes password_hash."""
        return {
            "owner_id": self.owner_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "date_added": self.date_added,
        }        