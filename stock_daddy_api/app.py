from flask import Flask
from app.controllers.owner_controller import owner_bp
from app.controllers.business_controller import business_bp
from app.controllers.building_controller import building_bp
from app.controllers.room_controller import room_bp
from app.controllers.storage_controller import storage_bp
from app.controllers.item_type_controller import item_type_bp
from app.controllers.item_controller import item_bp

app = Flask(__name__)
app.register_blueprint(owner_bp)
app.register_blueprint(business_bp)
app.register_blueprint(building_bp)
app.register_blueprint(room_bp)
app.register_blueprint(storage_bp)
app.register_blueprint(item_type_bp)
app.register_blueprint(item_bp)


if __name__ == "__main__":
    app.run(debug=True)