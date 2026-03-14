"""
config.py — Centralised configuration for Lead Agent.
Reads from environment variables (set via .env file).
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── API Keys ───────────────────────────────────────────────
GOOGLE_PLACES_API_KEY: str = os.getenv("GOOGLE_PLACES_API_KEY", "")
SERPAPI_KEY: str            = os.getenv("SERPAPI_KEY", "")

# ── Google Sheets ──────────────────────────────────────────
GOOGLE_SERVICE_ACCOUNT_JSON: str = os.getenv(
    "GOOGLE_SERVICE_ACCOUNT_JSON", "credentials/google_service_account.json"
)
GOOGLE_SPREADSHEET_ID: str = os.getenv("GOOGLE_SPREADSHEET_ID", "")

# ── Scraping ───────────────────────────────────────────────
MAX_WORKERS: int        = int(os.getenv("MAX_WORKERS", 5))
REQUEST_TIMEOUT: int    = int(os.getenv("REQUEST_TIMEOUT", 15))
MAX_RESULTS_PER_CITY: int = int(os.getenv("MAX_RESULTS_PER_CITY", 100))
ENABLE_PLAYWRIGHT: bool = os.getenv("ENABLE_PLAYWRIGHT", "true").lower() == "true"

# ── Output ─────────────────────────────────────────────────
OUTPUT_DIR: str = "output"

# ── CSV column order ───────────────────────────────────────
CSV_COLUMNS = [
    "Business Name",
    "Category",
    "City",
    "Address",
    "Phone Number",
    "Website",
    "Email",
    "Source URL",
]

# ── Logging ────────────────────────────────────────────────
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
