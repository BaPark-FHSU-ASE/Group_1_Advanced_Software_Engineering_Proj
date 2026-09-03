
class ItemType:
    def __init__(self, item_type_id, name, description, replacement_cost):
        self.item_type_id = item_type_id
        self.name = name
        self.description = description
        self.replacement_cost = replacement_cost

    @classmethod
    def from_row(cls, row):
        return cls(
            item_type_id=row["item_type_id"],
            name=row["name"],
            description=row["description"],
            replacement_cost=row["replacement_cost"],
        )

    def to_dict(self):
        return {
            "item_type_id": self.item_type_id,
            "name": self.name,
            "description": self.description,
            "replacement_cost": self.replacement_cost,
        }