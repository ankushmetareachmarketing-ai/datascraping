"""
email_extractor.py — Extract emails and phone numbers from raw text.

Handles:
  • Standard email regex with validation
  • Indian & international phone number formats
  • Blacklist filtering for fake/placeholder contacts
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Regex patterns
# ─────────────────────────────────────────────────────────────

# Email: RFC-5321-ish, avoids image filenames & CSS values
EMAIL_RE = re.compile(
    r"(?<![\/\w])"              # not preceded by slash or word char
    r"[a-zA-Z0-9._%+\-]{2,64}" # local part
    r"@"
    r"[a-zA-Z0-9.\-]{2,255}"   # domain
    r"\.[a-zA-Z]{2,10}"        # TLD
    r"(?![\/\w])",              # not followed by slash or word char
    re.IGNORECASE,
)

# Phone: supports +91, 0XX, ISD codes, separators
PHONE_RE = re.compile(
    r"(?<!\d)"
    r"("
    r"(?:\+?91[\s\-]?)?"                    # optional India country code
    r"(?:0\d{2,4}[\s\-]?)?"                 # optional STD code
    r"[6-9]\d{9}"                            # 10-digit mobile starting 6-9
    r"|"
    r"\+?\d{1,3}[\s.\-]?\(?\d{2,4}\)?[\s.\-]?\d{3,4}[\s.\-]?\d{3,4}"  # international
    r")"
    r"(?!\d)",
    re.VERBOSE,
)

# ─────────────────────────────────────────────────────────────
# Blacklists
# ─────────────────────────────────────────────────────────────

FAKE_EMAIL_PATTERNS = re.compile(
    r"(example\.|test@|noreply|no-reply|donotreply|sentry|"
    r"yourdomain|yourname|youremail|user@|admin@admin|"
    r"placeholder|info@example|sample@|email@email|"
    r"privacy@|abuse@|postmaster@|webmaster@|hostmaster@|"
    r"support@support|sales@sales|\.png|\.jpg|\.gif|\.css|\.js)",
    re.IGNORECASE,
)

SOCIAL_EMAIL_DOMAINS = {
    "facebook.com", "twitter.com", "instagram.com", "linkedin.com",
    "youtube.com", "t.co", "bit.ly", "tiktok.com",
}

# Phone numbers that are obviously fake / defaults
FAKE_PHONE_PATTERNS = re.compile(
    r"^(0{7,}|1{7,}|9{7,}|1234567890|0000000000|9999999999)$"
)


# ─────────────────────────────────────────────────────────────
# Extraction helpers
# ─────────────────────────────────────────────────────────────

def extract_emails(text: str) -> list[str]:
    """
    Extract and validate email addresses from a block of text.

    Returns a deduplicated list of clean email strings, with fakes removed.
    """
    if not text:
        return []

    raw_emails = EMAIL_RE.findall(text)
    seen: set[str] = set()
    valid: list[str] = []

    for email in raw_emails:
        email_lower = email.lower().strip()

        # Skip duplicates
        if email_lower in seen:
            continue
        seen.add(email_lower)

        # Skip fake/placeholder emails
        if FAKE_EMAIL_PATTERNS.search(email_lower):
            logger.debug("Skipping fake email: %s", email_lower)
            continue

        # Skip social media emails
        domain = email_lower.split("@")[-1]
        if domain in SOCIAL_EMAIL_DOMAINS:
            logger.debug("Skipping social-media email: %s", email_lower)
            continue

        # Basic sanity check: domain must have at least one dot
        parts = domain.split(".")
        if len(parts) < 2 or any(len(p) == 0 for p in parts):
            continue

        valid.append(email_lower)

    return valid


def extract_phones(text: str) -> list[str]:
    """
    Extract and normalise phone numbers from a block of text.

    Returns a deduplicated list of cleaned phone strings.
    """
    if not text:
        return []

    matches = PHONE_RE.findall(text)
    seen: set[str] = set()
    valid: list[str] = []

    for phone in matches:
        # Remove all non-digit characters for normalisation
        digits = re.sub(r"\D", "", phone)

        # Drop very short / very long sequences
        if len(digits) < 7 or len(digits) > 15:
            continue

        # Skip obvious fakes
        if FAKE_PHONE_PATTERNS.match(digits):
            continue

        # Normalise Indian mobile: strip leading 91 if 12 digits
        if len(digits) == 12 and digits.startswith("91"):
            digits = digits[2:]

        # Final check — 10-digit Indian mobile must start 6-9
        if len(digits) == 10 and digits[0] not in "6789":
            continue

        if digits not in seen:
            seen.add(digits)
            valid.append(digits)

    return valid


# ─────────────────────────────────────────────────────────────
# Schema.org / JSON-LD extraction
# ─────────────────────────────────────────────────────────────

def extract_from_jsonld(soup) -> dict:
    """
    Pull structured contact data from JSON-LD blocks on a page.
    Returns dict with 'email' and 'phone' keys (may be empty strings).
    """
    import json

    result = {"email": "", "phone": ""}

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            # Handle @graph arrays
            items = data if isinstance(data, list) else [data]
            for item in items:
                if not isinstance(item, dict):
                    continue
                if not result["email"]:
                    raw_email = item.get("email", "")
                    if raw_email:
                        cleaned = extract_emails(raw_email)
                        result["email"] = cleaned[0] if cleaned else ""
                if not result["phone"]:
                    raw_phone = item.get("telephone", "")
                    if raw_phone:
                        cleaned = extract_phones(raw_phone)
                        result["phone"] = cleaned[0] if cleaned else ""
                if result["email"] and result["phone"]:
                    return result
        except Exception:
            continue

    return result


# ─────────────────────────────────────────────────────────────
# Convenience wrapper
# ─────────────────────────────────────────────────────────────

def best_email(text: str) -> str:
    """Return the single best email from text, or empty string."""
    emails = extract_emails(text)
    return emails[0] if emails else ""


def best_phone(text: str) -> str:
    """Return the single best phone number from text, or empty string."""
    phones = extract_phones(text)
    return phones[0] if phones else ""
