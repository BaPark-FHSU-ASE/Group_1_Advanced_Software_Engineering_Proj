class Item:
    def __init__(self, item_id, item_type_id, storage_id, item_name, item_status, date_added=None):
        self.item_id = item_id
        self.item_type_id = item_type_id
        self.storage_id = storage_id
        self.item_name = item_name
        self.item_status = item_status
        self.date_added = date_added

    @classmethod
    def from_row(cls, row):
        return cls(
            item_id=row["item_id"],
            item_type_id=row["item_type_id"],
            storage_id=row["storage_id"],
            item_name=row["item_name"],
            item_status=row["item_status"],
            date_added=row["date_added"],
        )

    def to_dict(self):
        return {
            "item_id": self.item_id,
            "item_type_id": self.item_type_id,
            "storage_id": self.storage_id,
            "item_name": self.item_name,
            "item_status": self.item_status,
            "date_added": self.date_added,
        }