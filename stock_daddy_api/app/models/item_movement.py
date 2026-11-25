NO_PLACE = "—"


class ItemMovement:
   #One line of an item's history: 

    def __init__(self, item_movement_id, moved_at, from_status, to_status,
                 item_id, item_name, item_type, building, from_place, to_place):
        self.item_movement_id = item_movement_id
        self.moved_at = moved_at
        self.from_status = from_status
        self.to_status = to_status
        self.item_id = item_id
        self.item_name = item_name
        self.item_type = item_type
        self.building = building
        self.from_place = from_place
        self.to_place = to_place

    @classmethod
    def from_row(cls, row):
        return cls(
            item_movement_id=row["item_movement_id"],
            moved_at=row["moved_at"],
            from_status=row["from_status"],
            to_status=row["to_status"],
            item_id=row["item_id"],
            item_name=row["item_name"],
            item_type=row["item_type"],
            building=row["building"],
            from_place=row["from_place"],
            to_place=row["to_place"],
        )

    def to_dict(self):
        """The shape the frontend reads. Same wording as an item's own movement history."""
        return {
            "movement_id": self.item_movement_id,
            "date": (self.moved_at or NO_PLACE)[:10],
            "item_id": self.item_id,
            "item_name": self.item_name,
            "item_type": self.item_type,
            "building": self.building or NO_PLACE,
            "from": self.from_place or NO_PLACE,
            "to": self.to_place or NO_PLACE,
            # Set only when the row records a status change, e.g. "In Storage → In Transit".
            "status_change": (
                f"{self.from_status or NO_PLACE} → {self.to_status}" if self.to_status else None
            ),
        }
