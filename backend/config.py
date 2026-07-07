import os
from pathlib import Path


def _load_dotenv() -> None:
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()


APP_NAME = "Global Asset Shield Agent"
APP_ENV = os.getenv("APP_ENV", "development")
APP_VERSION = "V1.0 Beta"
APP_CONCEPT = "AI Investment Immune System"
APP_DESCRIPTION = "AI 投资免疫系统"

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATABASE_PATH = DATA_DIR / "investment_journal.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATABASE_PATH}")
KOL_RECORDS_PATH = DATA_DIR / "kol_records.json"

JWT_SECRET_KEY = os.getenv("JWT_SECRET", "global-asset-shield-local-secret-change-me")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(60 * 24 * 7)))

CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://127.0.0.1:5173,http://localhost:5173,http://localhost:3000").split(",")
    if origin.strip()
]

DEMO_EMAIL = os.getenv("DEMO_USER_EMAIL", "demo@globalassetshield.ai")
DEMO_PASSWORD = os.getenv("DEMO_USER_PASSWORD", "demo123456")
DEMO_USERNAME = os.getenv("DEMO_USER_USERNAME", "Demo User")

LLM_ENABLED = os.getenv("LLM_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_BASE = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
LLM_DAILY_LIMIT = int(os.getenv("LLM_DAILY_LIMIT", "20"))
LLM_TIMEOUT_SECONDS = int(os.getenv("LLM_TIMEOUT_SECONDS", "12"))

DEXSCREENER_SEARCH_URL = "https://api.dexscreener.com/latest/dex/search"
DEXSCREENER_TOKEN_URL = "https://api.dexscreener.com/latest/dex/tokens"

HOT_STOCKS = {"TSLA", "NVDA", "MSTR", "GME", "AMC"}
MEME_TOKENS = {"pepe", "doge", "shib", "meme"}
