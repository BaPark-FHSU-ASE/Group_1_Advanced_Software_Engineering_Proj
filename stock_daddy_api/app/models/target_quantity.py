class TargetQuantity:
    def __init__(self, target_quantity_id, building_id, item_type_id, target_qty):
        self.target_quantity_id = target_quantity_id
        self.building_id = building_id
        self.item_type_id = item_type_id
        self.target_qty = target_qty

    @classmethod
    def from_row(cls, row):
        return cls(
            target_quantity_id=row["target_quantity_id"],
            building_id=row["building_id"],
            item_type_id=row["item_type_id"],
            target_qty=row["target_qty"],
        )

    def to_dict(self):
        return {
            "target_quantity_id": self.target_quantity_id,
            "building_id": self.building_id,
            "item_type_id": self.item_type_id,
            "target_qty": self.target_qty,
        }
