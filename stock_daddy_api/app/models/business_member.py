class BusinessMember:
    # owner/employee

    def __init__(self, business_member_id, business_id, owner_id, role,
                 first_name=None, last_name=None, email=None):
        self.business_member_id = business_member_id
        self.business_id = business_id
        self.owner_id = owner_id
        self.role = role
        self.first_name = first_name
        self.last_name = last_name
        self.email = email

    @classmethod
    def from_row(cls, row):
        has_person = "first_name" in row.keys()
        return cls(
            business_member_id=row["business_member_id"],
            business_id=row["business_id"],
            owner_id=row["owner_id"],
            role=row["role"],
            first_name=row["first_name"] if has_person else None,
            last_name=row["last_name"] if has_person else None,
            email=row["email"] if has_person else None,
        )

    def to_dict(self):
        return {
            "business_member_id": self.business_member_id,
            "business_id": self.business_id,
            "owner_id": self.owner_id,
            "role": self.role,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
        }