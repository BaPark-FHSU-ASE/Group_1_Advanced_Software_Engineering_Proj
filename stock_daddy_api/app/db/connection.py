
import sqlite3
from app.config import Config


def get_connection():
    connection = sqlite3.connect(Config.DB_PATH)

    # Below will enforce foreign key constraints in sql lite
    connection.execute("PRAGMA foreign_keys = ON") 

    # retruns sqlite.row objects instead of tuples to allow for easier parcing of data
    connection.row_factory = sqlite3.Row

    return connection