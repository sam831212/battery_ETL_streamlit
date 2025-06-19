"""
Configuration utilities for the Battery ETL Dashboard
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# SQLite database configuration - single file database by default
DB_PATH = os.getenv("DB_PATH", "battery.db")
# 未來使用公用槽可能路徑
# DB_PATH = r"\\smpfile11.simplo.com.tw\Prj_share\TPRD_CA\電池應用部測試資料\0.測試資料程式處理\battery.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")

# Application settings
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "./uploads")
