class Room:
    def __init__(self, room_id, building_id, location, retired=None):
        self.room_id = room_id
        self.building_id = building_id
        self.location = location
        self.retired = retired

    @classmethod
    def from_row(cls, row):
        return cls(
            room_id=row["room_id"],
            building_id=row["building_id"],
            location=row["location"],
            retired=row["retired"],
        )

    def to_dict(self):
        return {
            "room_id": self.room_id,
            "building_id": self.building_id,
            "location": self.location,
            "retired": self.retired,
        }