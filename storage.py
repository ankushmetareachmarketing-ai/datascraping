"""
storage.py — Persist cleaned leads to CSV and/or Google Sheets.

Supports:
  • Local CSV  (always available)
  • Google Sheets via gspread  (requires service account credentials)
"""

import logging
import os
from datetime import datetime
from pathlib import Path

import pandas as pd

import config

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# CSV storage
# ─────────────────────────────────────────────────────────────

def save_to_csv(df: pd.DataFrame, city: str, category: str = "") -> str:
    """
    Save a DataFrame to a timestamped CSV file in the output directory.

    Returns:
        Absolute path to the created CSV file.
    """
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    cat_slug  = category.replace(" ", "_").lower() if category else "all"
    city_slug = city.replace(" ", "_").lower()
    filename  = f"{city_slug}_{cat_slug}_{timestamp}.csv"
    filepath  = Path(config.OUTPUT_DIR) / filename

    df.to_csv(filepath, index=False, encoding="utf-8-sig")  # utf-8-sig for Excel compatibility

    logger.info("Saved %d leads to %s", len(df), filepath)
    return str(filepath)


def load_csv(filepath: str) -> pd.DataFrame:
    """Load an existing lead CSV file."""
    return pd.read_csv(filepath, encoding="utf-8-sig")


def list_saved_files() -> list[str]:
    """Return list of CSV paths in the output directory."""
    out = Path(config.OUTPUT_DIR)
    if not out.exists():
        return []
    return sorted(str(p) for p in out.glob("*.csv"))


# ─────────────────────────────────────────────────────────────
# Google Sheets storage
# ─────────────────────────────────────────────────────────────

class GoogleSheetsStorage:
    """
    Append leads to a Google Sheet.

    Setup:
      1. Create a Google Cloud project and enable the Sheets API.
      2. Create a Service Account and download the JSON key.
      3. Share the target spreadsheet with the service account email.
      4. Set GOOGLE_SERVICE_ACCOUNT_JSON and GOOGLE_SPREADSHEET_ID in .env
    """

    def __init__(self):
        self._gc        = None
        self._sheet     = None
        self._worksheet = None

    def _connect(self):
        """Lazy-connect to Google Sheets."""
        if self._gc:
            return

        try:
            import gspread
            from google.oauth2.service_account import Credentials

            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ]

            cred_path = config.GOOGLE_SERVICE_ACCOUNT_JSON
            if not os.path.exists(cred_path):
                raise FileNotFoundError(
                    f"Service account JSON not found at: {cred_path}\n"
                    "Set GOOGLE_SERVICE_ACCOUNT_JSON in .env"
                )

            creds = Credentials.from_service_account_file(cred_path, scopes=scopes)
            self._gc = gspread.authorize(creds)
            logger.info("Connected to Google Sheets API.")

        except ImportError:
            raise ImportError(
                "gspread not installed. Run: pip install gspread google-auth"
            )

    def _get_or_create_worksheet(self, spreadsheet_id: str, tab_name: str):
        """Return existing worksheet or create a new tab."""
        self._connect()
        spreadsheet = self._gc.open_by_key(spreadsheet_id)

        try:
            ws = spreadsheet.worksheet(tab_name)
        except Exception:
            ws = spreadsheet.add_worksheet(title=tab_name, rows=5000, cols=20)
            # Add header row to new sheet
            ws.append_row(config.CSV_COLUMNS, value_input_option="RAW")
            logger.info("Created new worksheet: %s", tab_name)

        return ws

    def append(
        self,
        df: pd.DataFrame,
        city: str,
        category: str = "",
        spreadsheet_id: str = "",
    ) -> str:
        """
        Append leads to a Google Sheet tab named after the city.

        Args:
            df:             Cleaned leads DataFrame.
            city:           City name (used as worksheet tab name).
            category:       Optional category (appended to tab name).
            spreadsheet_id: Override spreadsheet ID (default from config).

        Returns:
            URL of the Google Sheet.
        """
        sid  = spreadsheet_id or config.GOOGLE_SPREADSHEET_ID
        if not sid:
            raise ValueError(
                "No spreadsheet ID configured. "
                "Set GOOGLE_SPREADSHEET_ID in .env"
            )

        tab_name = f"{city} - {category}" if category else city
        ws = self._get_or_create_worksheet(sid, tab_name)

        # Check if sheet is empty (only header row)
        existing = ws.get_all_values()
        if len(existing) <= 1:
            # Write header
            ws.update([config.CSV_COLUMNS], "A1")

        # Append data rows
        rows = df[config.CSV_COLUMNS].fillna("").values.tolist()
        ws.append_rows(rows, value_input_option="USER_ENTERED")

        url = f"https://docs.google.com/spreadsheets/d/{sid}"
        logger.info("Uploaded %d rows to Google Sheets: %s", len(rows), url)
        return url


# ─────────────────────────────────────────────────────────────
# Convenience wrappers
# ─────────────────────────────────────────────────────────────

_gsheets = GoogleSheetsStorage()   # singleton


def save_to_sheets(
    df: pd.DataFrame,
    city: str,
    category: str = "",
    spreadsheet_id: str = "",
) -> str:
    """Save leads to Google Sheets. Returns sheet URL."""
    return _gsheets.append(df, city, category, spreadsheet_id)


def export_all_cities(city_results: dict[str, pd.DataFrame]) -> list[str]:
    """
    Export multiple city DataFrames to separate CSV files.

    Args:
        city_results: {"City Name": df, ...}

    Returns:
        List of saved file paths.
    """
    paths = []
    for city, df in city_results.items():
        if df is not None and not df.empty:
            path = save_to_csv(df, city)
            paths.append(path)
    return paths
