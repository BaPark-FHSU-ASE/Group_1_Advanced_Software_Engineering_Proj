import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    DB_PATH = os.getenv("DB_PATH", "../frontend/stockdaddy.db")
    FLASK_DEBUG = os.getenv("FLASK_DEBUG", "True") == "True"