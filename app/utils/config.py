"""
Configuration utilities for the Battery ETL Dashboard
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database configuration
DB_PATH = os.getenv("DB_PATH", "battery.db")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")

# Application settings
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "./uploads")
