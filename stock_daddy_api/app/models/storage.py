class Storage:
    def __init__(self, storage_id, room_id, storage_type):
        self.storage_id = storage_id
        self.room_id = room_id
        self.storage_type = storage_type

    @classmethod
    def from_row(cls, row):
        return cls(
            storage_id=row["storage_id"],
            room_id=row["room_id"],
            storage_type=row["storage_type"],
        )

    def to_dict(self):
        return {
            "storage_id": self.storage_id,
            "room_id": self.room_id,
            "storage_type": self.storage_type,
        }