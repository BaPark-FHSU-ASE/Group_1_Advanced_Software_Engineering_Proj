class Building:
    def __init__(self, building_id, business_id, state, city, street_address, retired=None):
        self.building_id = building_id
        self.business_id = business_id
        self.state = state
        self.city = city
        self.street_address = street_address
        self.retired = retired

    @classmethod
    def from_row(cls, row):
        return cls(
            building_id=row["building_id"],
            business_id=row["business_id"],
            state=row["state"],
            city=row["city"],
            street_address=row["street_address"],
            retired=row["retired"],
        )

    def to_dict(self):
        return {
            "building_id": self.building_id,
            "business_id": self.business_id,
            "state": self.state,
            "city": self.city,
            "street_address": self.street_address,
            "retired": self.retired,
        }