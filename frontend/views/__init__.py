"""The frontend's pages, one blueprint per area.

    auth          login, register, logout
    dashboard     the Dashboard and its business buttons
    buildings     a building's page, its rooms, storage units and targets
    items         the item list, adding items, an item's page
    item_types    item types (REQ-9)
    routes        route costs between buildings (REQ-17)
    compliance    Surplus & Shortage
    redistribute  the optimizer page

app.py registers them all; nothing here creates the Flask app itself.
"""

from views.auth import bp as auth_bp
from views.buildings import bp as buildings_bp
from views.compliance import bp as compliance_bp
from views.dashboard import bp as dashboard_bp
from views.item_types import bp as item_types_bp
from views.items import bp as items_bp
from views.redistribute import bp as redistribute_bp
from views.routes import bp as routes_bp

ALL_BLUEPRINTS = (
    auth_bp,
    dashboard_bp,
    buildings_bp,
    items_bp,
    item_types_bp,
    routes_bp,
    compliance_bp,
    redistribute_bp,
)
