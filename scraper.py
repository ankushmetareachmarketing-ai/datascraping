"""
scraper.py — Website contact scraper.

For each business URL, this module:
  1. Fetches the homepage with requests + BeautifulSoup
  2. Discovers contact/about/footer subpages
  3. Extracts emails and phones from page text
  4. Falls back to Playwright for JS-rendered pages

Usage:
    from scraper import scrape_website
    result = scrape_website("https://example.com")
    # {"email": "info@example.com", "phone": "9876543210"}
"""

import logging
import re
import time
import urllib.parse
from typing import Optional

import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

import config
from email_extractor import (
    extract_emails, extract_phones,
    extract_from_jsonld, best_email, best_phone
)

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────

# Subpages to check for contact info
CONTACT_SLUGS = [
    "contact", "contact-us", "contactus",
    "about",   "about-us",   "aboutus",
    "reach",   "reach-us",
    "get-in-touch",
    "support",
    "enquiry", "inquiry",
]

# CSS selectors that commonly hold contact info
CONTACT_SELECTORS = [
    "footer", "#footer", ".footer",
    "[class*='contact']", "[id*='contact']",
    "[class*='address']", "[id*='address']",
    "address",
    "[class*='phone']",  "[id*='phone']",
    "[class*='email']",  "[id*='email']",
    "[class*='touch']",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


# ─────────────────────────────────────────────────────────────
# HTTP helpers
# ─────────────────────────────────────────────────────────────

@retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=5))
def _fetch_html(url: str, session: requests.Session) -> Optional[str]:
    """Return page HTML string or None on failure."""
    try:
        resp = session.get(
            url,
            headers=HEADERS,
            timeout=config.REQUEST_TIMEOUT,
            allow_redirects=True,
        )
        if resp.status_code == 200:
            return resp.text
        logger.debug("HTTP %s for %s", resp.status_code, url)
    except requests.RequestException as exc:
        logger.debug("Request failed for %s: %s", url, exc)
    return None


def _normalise_url(base: str, href: str) -> str:
    """Resolve a possibly-relative href against a base URL."""
    if href.startswith("http"):
        return href
    return urllib.parse.urljoin(base, href)


def _is_same_domain(base: str, url: str) -> bool:
    base_netloc = urllib.parse.urlparse(base).netloc.lstrip("www.")
    url_netloc  = urllib.parse.urlparse(url).netloc.lstrip("www.")
    return base_netloc == url_netloc


# ─────────────────────────────────────────────────────────────
# Page parser
# ─────────────────────────────────────────────────────────────

def _parse_page(html: str, base_url: str) -> dict:
    """
    Parse HTML for emails, phones, and links to contact subpages.

    Returns:
        {
          "email":  str,
          "phone":  str,
          "links":  list[str],   # candidate contact-page URLs
        }
    """
    soup = BeautifulSoup(html, "lxml")

    # 1. Remove script/style noise
    for tag in soup(["script", "style", "noscript", "head"]):
        tag.decompose()

    # 2. JSON-LD structured data (highest confidence)
    structured = extract_from_jsonld(soup)
    email_found = structured["email"]
    phone_found = structured["phone"]

    # 3. Check mailto: links
    if not email_found:
        for a in soup.find_all("a", href=re.compile(r"^mailto:", re.I)):
            mailto = a["href"].replace("mailto:", "").split("?")[0].strip()
            candidates = extract_emails(mailto)
            if candidates:
                email_found = candidates[0]
                break

    # 4. Check tel: links
    if not phone_found:
        for a in soup.find_all("a", href=re.compile(r"^tel:", re.I)):
            tel = a["href"].replace("tel:", "").strip()
            candidates = extract_phones(tel)
            if candidates:
                phone_found = candidates[0]
                break

    # 5. Scan high-priority contact sections
    if not email_found or not phone_found:
        for selector in CONTACT_SELECTORS:
            node = soup.select_one(selector)
            if not node:
                continue
            text = node.get_text(" ", strip=True)
            if not email_found:
                emails = extract_emails(text)
                if emails:
                    email_found = emails[0]
            if not phone_found:
                phones = extract_phones(text)
                if phones:
                    phone_found = phones[0]
            if email_found and phone_found:
                break

    # 6. Full page text fallback
    if not email_found or not phone_found:
        full_text = soup.get_text(" ", strip=True)
        if not email_found:
            email_found = best_email(full_text)
        if not phone_found:
            phone_found = best_phone(full_text)

    # 7. Discover contact subpage links
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"].lower()
        text = a.get_text(strip=True).lower()
        # Match slug patterns in href or link text
        if any(slug in href or slug in text for slug in CONTACT_SLUGS):
            full = _normalise_url(base_url, a["href"])
            if _is_same_domain(base_url, full) and full not in links:
                links.append(full)

    return {"email": email_found, "phone": phone_found, "links": links[:5]}


# ─────────────────────────────────────────────────────────────
# Playwright fallback
# ─────────────────────────────────────────────────────────────

def _fetch_with_playwright(url: str) -> Optional[str]:
    """
    Render a JS-heavy page with Playwright and return its HTML.
    Only used when requests returns no useful content.
    """
    if not config.ENABLE_PLAYWRIGHT:
        return None

    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page    = browser.new_page(user_agent=HEADERS["User-Agent"])
            try:
                page.goto(url, timeout=config.REQUEST_TIMEOUT * 1000, wait_until="domcontentloaded")
                page.wait_for_timeout(2000)   # let JS settle
                html = page.content()
            except PWTimeout:
                html = None
            finally:
                browser.close()
        return html

    except ImportError:
        logger.debug("Playwright not installed. Skipping JS fallback.")
    except Exception as exc:
        logger.debug("Playwright error for %s: %s", url, exc)
    return None


# ─────────────────────────────────────────────────────────────
# Main public interface
# ─────────────────────────────────────────────────────────────

def scrape_website(url: str) -> dict:
    """
    Scrape a business website for contact details.

    Steps:
      1. Fetch homepage via requests
      2. Parse for emails/phones/contact links
      3. Follow contact subpages if needed
      4. Playwright fallback for JS-rendered pages

    Args:
        url: Full URL including scheme (e.g., "https://business.com")

    Returns:
        {"email": str, "phone": str}
    """
    if not url or not url.startswith("http"):
        return {"email": "", "phone": ""}

    logger.info("Scraping: %s", url)

    session = requests.Session()
    session.headers.update(HEADERS)

    email = ""
    phone = ""

    # ── Step 1: Homepage ──────────────────────────────────
    html = _fetch_html(url, session)
    js_fallback_needed = False

    if html:
        parsed = _parse_page(html, url)
        email = parsed["email"]
        phone = parsed["phone"]
        contact_links = parsed["links"]

        # Check if page looks JS-rendered (very little text)
        if len(BeautifulSoup(html, "lxml").get_text(strip=True)) < 200:
            js_fallback_needed = True
    else:
        contact_links = []
        js_fallback_needed = True

    # ── Step 2: Playwright fallback ────────────────────────
    if js_fallback_needed and config.ENABLE_PLAYWRIGHT:
        logger.debug("Trying Playwright for %s", url)
        pw_html = _fetch_with_playwright(url)
        if pw_html:
            parsed = _parse_page(pw_html, url)
            email = email or parsed["email"]
            phone = phone or parsed["phone"]
            contact_links = contact_links or parsed["links"]

    # ── Step 3: Contact subpages ───────────────────────────
    if (not email or not phone) and contact_links:
        for link in contact_links:
            if email and phone:
                break
            logger.debug("Checking contact subpage: %s", link)
            sub_html = _fetch_html(link, session)

            # Playwright fallback for subpages too
            if not sub_html and config.ENABLE_PLAYWRIGHT:
                sub_html = _fetch_with_playwright(link)

            if sub_html:
                sub = _parse_page(sub_html, link)
                email = email or sub["email"]
                phone = phone or sub["phone"]

            time.sleep(0.5)   # polite crawl delay

    session.close()

    result = {"email": email, "phone": phone}
    logger.info("Result for %s → email=%s  phone=%s", url, email or "—", phone or "—")
    return result


# ─────────────────────────────────────────────────────────────
# Batch scraper
# ─────────────────────────────────────────────────────────────

def scrape_leads(leads: list[dict], progress_callback=None) -> list[dict]:
    """
    Enrich a list of lead dicts with email and phone from their websites.

    Args:
        leads:             List of lead dicts (must have "Website" key).
        progress_callback: Optional callable(current, total) for UI progress updates.

    Returns:
        Same list with "Email" and "Phone Number" fields populated where found.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    total = len(leads)

    def _enrich(idx_lead):
        idx, lead = idx_lead
        website = lead.get("Website", "").strip()

        if website:
            try:
                result = scrape_website(website)
                lead["Email"]        = lead.get("Email") or result["email"]
                lead["Phone Number"] = lead.get("Phone Number") or result["phone"]
            except Exception as exc:
                logger.warning("Scrape error for %s: %s", website, exc)

        # Wrap in try/except — Streamlit progress callbacks crash in threads
        # (missing ScriptRunContext), which would silently drop the lead.
        if progress_callback:
            try:
                progress_callback(idx + 1, total)
            except Exception:
                pass  # Never let UI errors kill a lead

        return lead  # Always reached now

    enriched = []
    with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
        futures = {
            executor.submit(_enrich, (i, lead)): i
            for i, lead in enumerate(leads)
        }
        for future in as_completed(futures):
            try:
                result = future.result()
                if result is not None:
                    enriched.append(result)
            except Exception as exc:
                logger.error("Thread error: %s", exc)

    # Build an index for stable sort — guard against any missing entries
    order = {id(lead): i for i, lead in enumerate(leads)}
    enriched.sort(key=lambda x: order.get(id(x), 0))
    return enriched
