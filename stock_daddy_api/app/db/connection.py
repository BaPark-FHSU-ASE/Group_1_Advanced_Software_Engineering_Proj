
import sqlite3

from flask import g, has_app_context

from app.config import Config


def get_connection():
    connection = sqlite3.connect(Config.DB_PATH)


    connection.execute("PRAGMA foreign_keys = ON") #Enforces foreign keys

    connection.row_factory = sqlite3.Row


    if has_app_context():
        g.setdefault("open_connections", []).append(connection)

    return connection


def close_connections(exception=None):
    """Close every connection opened during this request (safe to repeat)."""
    for connection in g.pop("open_connections", []):
        connection.close()