class Business:
    def __init__(self, business_id, name, owner_id):
        self.business_id = business_id
        self.name = name
        self.owner_id = owner_id
        
    @classmethod
    def from_row(cls, row):
        return cls(
            business_id=row["business_id"],
            name=row["name"],
            owner_id=row["owner_id"],
        )       
    
    def to_dict(self):
        return {
            "business_id": self.business_id,
            "name": self.name,
            "owner_id": self.owner_id,
        }    
      