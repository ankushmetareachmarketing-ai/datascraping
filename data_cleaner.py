"""
data_cleaner.py — Lead deduplication, validation, and normalisation.

Uses pandas for bulk operations. Applies the following pipeline:
  1. Normalise column types (strip whitespace, lowercase emails)
  2. Validate email addresses
  3. Validate phone numbers
  4. Deduplicate (by name+city, by email, by phone)
  5. Fill unknown fields with empty string (no NaN in CSV output)
  6. Score each lead (completeness 0-4) for sorting
"""

import logging
import re

import pandas as pd

import config

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Validators
# ─────────────────────────────────────────────────────────────

_EMAIL_SIMPLE = re.compile(
    r"^[a-zA-Z0-9._%+\-]{2,64}@[a-zA-Z0-9.\-]{2,255}\.[a-zA-Z]{2,10}$"
)

_FAKE_EMAIL = re.compile(
    r"(example\.|noreply|no-reply|donotreply|placeholder|yourdomain|"
    r"yourname|youremail|@example|@test\.|@domain\.|privacy@|abuse@|"
    r"postmaster@|webmaster@|hostmaster@)",
    re.IGNORECASE,
)

_PHONE_DIGITS = re.compile(r"\d+")


def _is_valid_email(email: str) -> bool:
    if not email or not isinstance(email, str):
        return False
    email = email.strip().lower()
    if not _EMAIL_SIMPLE.match(email):
        return False
    if _FAKE_EMAIL.search(email):
        return False
    return True


def _is_valid_phone(phone: str) -> bool:
    if not phone or not isinstance(phone, str):
        return False
    digits = "".join(_PHONE_DIGITS.findall(phone))
    # Strip leading country code 91
    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    return 7 <= len(digits) <= 15


def _normalise_phone(phone: str) -> str:
    """Return only digit string (strips formatting chars)."""
    if not phone:
        return ""
    return "".join(_PHONE_DIGITS.findall(str(phone)))


# ─────────────────────────────────────────────────────────────
# Main cleaning pipeline
# ─────────────────────────────────────────────────────────────

def clean_leads(leads: list[dict]) -> pd.DataFrame:
    """
    Run the full cleaning pipeline on a list of raw lead dicts.

    Args:
        leads: Raw leads from maps_search + scraper.

    Returns:
        Cleaned, sorted pandas DataFrame.
    """
    if not leads:
        logger.warning("clean_leads received empty list.")
        return pd.DataFrame(columns=config.CSV_COLUMNS)

    df = pd.DataFrame(leads)

    # Ensure all expected columns exist (base + targeting extras)
    extended_cols = config.CSV_COLUMNS + ["Services Needed", "Lead Tier", "Tier Badge", "Sales Pitch"]
    for col in extended_cols:
        if col not in df.columns:
            df[col] = ""

    # Keep only the extended set
    available = [c for c in extended_cols if c in df.columns]
    df = df[available].copy()

    # ── 1. Normalise strings ──────────────────────────────
    str_cols = ["Business Name", "Category", "City", "Address",
                "Phone Number", "Website", "Email", "Source URL"]
    for col in str_cols:
        df[col] = df[col].fillna("").astype(str).str.strip()

    df["Email"] = df["Email"].str.lower()

    # Normalise phone digits
    df["Phone Number"] = df["Phone Number"].apply(_normalise_phone)

    # ── 2. Validate emails ────────────────────────────────
    invalid_email_mask = df["Email"].apply(
        lambda e: bool(e) and not _is_valid_email(e)
    )
    df.loc[invalid_email_mask, "Email"] = ""
    n_inv_email = invalid_email_mask.sum()
    if n_inv_email:
        logger.info("Cleared %d invalid email(s).", n_inv_email)

    # ── 3. Validate phones ────────────────────────────────
    invalid_phone_mask = df["Phone Number"].apply(
        lambda p: bool(p) and not _is_valid_phone(p)
    )
    df.loc[invalid_phone_mask, "Phone Number"] = ""
    n_inv_phone = invalid_phone_mask.sum()
    if n_inv_phone:
        logger.info("Cleared %d invalid phone(s).", n_inv_phone)

    # ── 4. Remove rows with no business name ──────────────
    before = len(df)
    df = df[df["Business Name"].str.len() > 0].copy()
    logger.info("Removed %d rows with empty business name.", before - len(df))

    # ── 5. Deduplicate ────────────────────────────────────
    before = len(df)

    # a) Same name + city (case-insensitive)
    df["_name_city"] = (
        df["Business Name"].str.lower() + "|" + df["City"].str.lower()
    )
    df = df.drop_duplicates(subset=["_name_city"], keep="first")

    # b) Same non-empty email
    email_dupes = df["Email"] != ""
    df_email    = df[email_dupes].drop_duplicates(subset=["Email"], keep="first")
    df_no_email = df[~email_dupes]
    df = pd.concat([df_email, df_no_email], ignore_index=True)

    # c) Same non-empty phone
    phone_dupes = df["Phone Number"] != ""
    df_phone    = df[phone_dupes].drop_duplicates(subset=["Phone Number"], keep="first")
    df_no_phone = df[~phone_dupes]
    df = pd.concat([df_phone, df_no_phone], ignore_index=True)

    # Drop helper column
    df.drop(columns=["_name_city"], errors="ignore", inplace=True)

    logger.info("Deduplicated: %d → %d rows.", before, len(df))

    # ── 6. Completeness score & sort ──────────────────────
    df["_score"] = (
        (df["Email"]        != "").astype(int) * 2 +   # email = 2 pts (most valuable)
        (df["Phone Number"] != "").astype(int) * 2 +   # phone = 2 pts
        (df["Website"]      != "").astype(int) +
        (df["Address"]      != "").astype(int)
    )
    df = df.sort_values("_score", ascending=False)
    df.drop(columns=["_score"], inplace=True)

    # ── 7. Final cleanup ─────────────────────────────────
    df = df.fillna("").reset_index(drop=True)

    logger.info("Cleaning complete. Final row count: %d", len(df))
    return df


def get_stats(df: pd.DataFrame) -> dict:
    """
    Return a summary statistics dict for a cleaned DataFrame.
    Used by the UI to display pipeline results.
    """
    return {
        "total":         len(df),
        "with_email":    int((df["Email"]        != "").sum()),
        "with_phone":    int((df["Phone Number"] != "").sum()),
        "with_website":  int((df["Website"]      != "").sum()),
        "with_address":  int((df["Address"]      != "").sum()),
        "fully_complete": int(
            ((df["Email"] != "") & (df["Phone Number"] != "")).sum()
        ),
    }
