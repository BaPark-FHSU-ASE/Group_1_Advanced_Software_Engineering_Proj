class BuildingRoute:

    def __init__(self, building_route_id, from_building_id, to_building_id,
                 distance_miles, fixed_dispatch_cost, cost_per_unit_mile,
                 handling_cost_per_unit):
        self.building_route_id = building_route_id
        self.from_building_id = from_building_id
        self.to_building_id = to_building_id
        self.distance_miles = distance_miles
        self.fixed_dispatch_cost = fixed_dispatch_cost
        self.cost_per_unit_mile = cost_per_unit_mile
        self.handling_cost_per_unit = handling_cost_per_unit

    @classmethod
    def from_row(cls, row):
        return cls(
            building_route_id=row["building_route_id"],
            from_building_id=row["from_building_id"],
            to_building_id=row["to_building_id"],
            distance_miles=row["distance_miles"],
            fixed_dispatch_cost=row["fixed_dispatch_cost"],
            cost_per_unit_mile=row["cost_per_unit_mile"],
            handling_cost_per_unit=row["handling_cost_per_unit"],
        )

    def to_dict(self, from_label=None, to_label=None):
        """The shape the frontend reads. The labels are the buildings' names as
        the person sees them (see building_route_repository.building_labels)."""
        return {
            "route_id": self.building_route_id,
            "from_building_id": self.from_building_id,
            "from_label": from_label,
            "to_building_id": self.to_building_id,
            "to_label": to_label,
            "distance_miles": self.distance_miles,
            "fixed_dispatch_cost": self.fixed_dispatch_cost,
            "cost_per_unit_mile": self.cost_per_unit_mile,
            # Stored as distance x rate; rounded so 0.46 doesn't print as 0.45999999999999996.
            "handling_cost_per_unit": round(self.handling_cost_per_unit, 4),
        }