class BusinessMember:
# owner/employee

    def __init__(self, business_member_id, business_id, owner_id, role):
        self.business_member_id = business_member_id
        self.business_id = business_id
        self.owner_id = owner_id
        self.role = role

    @classmethod
    def from_row(cls, row):
        return cls(
            business_member_id=row["business_member_id"],
            business_id=row["business_id"],
            owner_id=row["owner_id"],
            role=row["role"],
        )

    def to_dict(self):
        return {
            "business_member_id": self.business_member_id,
            "business_id": self.business_id,
            "owner_id": self.owner_id,
            "role": self.role,
        }