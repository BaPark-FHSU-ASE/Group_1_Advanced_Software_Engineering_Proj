from flask import Flask
from app.controllers.owner_controller import owner_bp
from app.controllers.business_controller import business_bp

app = Flask(__name__)
app.register_blueprint(owner_bp)
app.register_blueprint(business_bp)


if __name__ == "__main__":
    app.run(debug=True)