"""Stock Daddy frontend.

This file only builds the Flask app. The pages themselves live in views/,
one blueprint per area (see views/__init__.py for the list).
"""

from flask import Flask

import api_launcher
from views import ALL_BLUEPRINTS


def create_app():
    app = Flask(__name__)
    app.secret_key = "dev-secret-key"  # Change before production
    for blueprint in ALL_BLUEPRINTS:
        app.register_blueprint(blueprint)
    return app


app = create_app()


if __name__ == "__main__":
    # Starts the Stock Daddy API too, so this one command runs both servers.
    api_launcher.start_api()
    app.run(debug=True)
