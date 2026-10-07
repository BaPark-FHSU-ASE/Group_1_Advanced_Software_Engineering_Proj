import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    DB_PATH = os.getenv("DB_PATH", "../frontend/stockdaddy.db")
    FLASK_DEBUG = os.getenv("FLASK_DEBUG", "True") == "True"
    # 5001 so the API can run beside the frontend, which uses Flask's
    # default port 5000.
    API_PORT = int(os.getenv("API_PORT", "5001"))