
class Room:
    def __init__(self, room_id, building_id, location):
        self.room_id = room_id
        self.building_id = building_id
        self.location = location

    @classmethod
    def from_row(cls, row):
        return cls(
            room_id=row["room_id"],
            building_id=row["building_id"],
            location=row["location"],
        )

    def to_dict(self):
        return {
            "room_id": self.room_id,
            "building_id": self.building_id,
            "location": self.location,
        }