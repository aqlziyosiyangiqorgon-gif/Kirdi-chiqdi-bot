import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
DB_NAME = os.getenv("DB_NAME", str(BASE_DIR / "finance.db"))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ADMIN_IDS_RAW = os.getenv("ADMIN_ID", "6273865667")
ADMIN_IDS = [int(i.strip()) for i in ADMIN_IDS_RAW.split(",") if i.strip().isdigit()]
ADMIN_ID = ADMIN_IDS[0] if ADMIN_IDS else 6273865667
DATABASE_URL = os.getenv("DATABASE_URL", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")





