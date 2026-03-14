"""
maps_search.py — Business discovery module.

Priority order:
  1. Google Places API  (most reliable, requires API key)
  2. SerpAPI Google Maps endpoint  (fallback, requires API key)
  3. DuckDuckGo HTML scraping  (free fallback, rate-limited)

Each strategy returns a list of dicts with keys matching CSV_COLUMNS.
"""

import logging
import time
import urllib.parse
from typing import Optional

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

import config

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Data model helper
# ─────────────────────────────────────────────────────────────

def _empty_lead(city: str, category: str) -> dict:
    """Return a blank lead skeleton."""
    return {
        "Business Name": "",
        "Category":      category,
        "City":          city,
        "Address":       "",
        "Phone Number":  "",
        "Website":       "",
        "Email":         "",
        "Source URL":    "",
    }


# ─────────────────────────────────────────────────────────────
# Strategy 1 — Google Places API
# ─────────────────────────────────────────────────────────────

class GooglePlacesSearcher:
    """
    Uses the Google Places Text Search + Place Details APIs.
    Docs: https://developers.google.com/maps/documentation/places/web-service
    """

    SEARCH_URL  = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"

    def __init__(self, api_key: str):
        self.api_key = api_key

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    def _text_search(self, query: str, page_token: str = "") -> dict:
        params = {
            "query":  query,
            "key":    self.api_key,
            "fields": "place_id,name,formatted_address,types",
        }
        if page_token:
            params["pagetoken"] = page_token
        resp = requests.get(self.SEARCH_URL, params=params, timeout=config.REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    def _place_details(self, place_id: str) -> dict:
        params = {
            "place_id": place_id,
            "fields":   "name,formatted_address,formatted_phone_number,website,types",
            "key":      self.api_key,
        }
        resp = requests.get(self.DETAILS_URL, params=params, timeout=config.REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json().get("result", {})

    def search(self, city: str, category: str = "", max_results: int = 60) -> list[dict]:
        query = f"{category} in {city}" if category else f"businesses in {city}"
        logger.info("[GooglePlaces] Searching: %s", query)

        leads      = []
        page_token = ""

        while len(leads) < max_results:
            data     = self._text_search(query, page_token)
            results  = data.get("results", [])

            for place in results:
                if len(leads) >= max_results:
                    break

                place_id = place.get("place_id", "")
                details  = self._place_details(place_id) if place_id else {}

                # Derive category from Google types list
                raw_types  = details.get("types", place.get("types", []))
                cat_label  = category or _types_to_label(raw_types)

                lead = _empty_lead(city, cat_label)
                lead["Business Name"] = details.get("name") or place.get("name", "")
                lead["Address"]       = details.get("formatted_address") or place.get("formatted_address", "")
                lead["Phone Number"]  = details.get("formatted_phone_number", "")
                lead["Website"]       = details.get("website", "")
                lead["Source URL"]    = f"https://maps.google.com/?place_id={place_id}"
                leads.append(lead)

            # Pagination
            page_token = data.get("next_page_token", "")
            if not page_token:
                break
            time.sleep(2)  # Google requires a short delay before using next_page_token

        logger.info("[GooglePlaces] Found %d results for '%s'", len(leads), query)
        return leads


def _types_to_label(types: list[str]) -> str:
    """Convert Google Places types list to a human-readable label."""
    skip = {"point_of_interest", "establishment", "geocode", "premise"}
    for t in types:
        if t not in skip:
            return t.replace("_", " ").title()
    return "Business"


# ─────────────────────────────────────────────────────────────
# Strategy 2 — SerpAPI Google Maps
# ─────────────────────────────────────────────────────────────

class SerpAPISearcher:
    """
    Uses SerpAPI's Google Maps endpoint as a fallback.
    Docs: https://serpapi.com/google-maps-api
    """

    BASE_URL = "https://serpapi.com/search"

    def __init__(self, api_key: str):
        self.api_key = api_key

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    def _fetch(self, params: dict) -> dict:
        resp = requests.get(self.BASE_URL, params=params, timeout=config.REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json()

    def search(self, city: str, category: str = "", max_results: int = 60) -> list[dict]:
        query = f"{category} in {city}" if category else f"top businesses in {city}"
        logger.info("[SerpAPI] Searching: %s", query)

        params = {
            "engine":  "google_maps",
            "q":       query,
            "api_key": self.api_key,
            "type":    "search",
            "hl":      "en",
        }

        leads  = []
        start  = 0

        while len(leads) < max_results:
            params["start"] = start
            data = self._fetch(params)

            local_results = data.get("local_results", [])
            if not local_results:
                break

            for place in local_results:
                if len(leads) >= max_results:
                    break

                lead = _empty_lead(city, category or place.get("type", "Business"))
                lead["Business Name"] = place.get("title", "")
                lead["Address"]       = place.get("address", "")
                lead["Phone Number"]  = place.get("phone", "")
                lead["Website"]       = place.get("website", "")
                lead["Source URL"]    = place.get("place_id_search", "")
                leads.append(lead)

            if len(local_results) < 20:
                break  # No more pages
            start += 20

        logger.info("[SerpAPI] Found %d results for '%s'", len(leads), query)
        return leads


# ─────────────────────────────────────────────────────────────
# Strategy 3 — Free fallback: DuckDuckGo + Google Maps HTML
# ─────────────────────────────────────────────────────────────

class FreeSearcher:
    """
    Zero-API fallback using DuckDuckGo Instant Answer API and
    public Google Maps HTML search scraping.
    NOTE: This is slower and less reliable. Use only when no API keys exist.
    """

    DDG_URL  = "https://api.duckduckgo.com/"
    MAPS_URL = "https://www.google.com/maps/search/"

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    }

    def search(self, city: str, category: str = "", max_results: int = 20) -> list[dict]:
        """
        Query DuckDuckGo for business listings.
        Returns fewer results than API-based methods — use for demos / testing.
        """
        query  = f"{category} {city} contact website" if category else f"businesses {city}"
        logger.info("[FreeSearch] Searching DuckDuckGo: %s", query)

        params = {
            "q":      query,
            "format": "json",
            "no_html": 1,
            "skip_disambig": 1,
        }

        leads = []
        try:
            resp = requests.get(
                self.DDG_URL, params=params,
                headers=self.HEADERS, timeout=config.REQUEST_TIMEOUT
            )
            resp.raise_for_status()
            data = resp.json()

            # Extract RelatedTopics as approximate business listings
            for item in data.get("RelatedTopics", [])[:max_results]:
                if isinstance(item, dict) and item.get("FirstURL"):
                    lead = _empty_lead(city, category or "Business")
                    lead["Business Name"] = item.get("Text", "")[:80]
                    lead["Website"]       = item.get("FirstURL", "")
                    lead["Source URL"]    = item.get("FirstURL", "")
                    leads.append(lead)

        except Exception as exc:
            logger.warning("[FreeSearch] DuckDuckGo failed: %s", exc)

        # Supplement with a Google Maps HTML scrape
        leads += self._scrape_google_maps_html(city, category, max_results - len(leads))
        logger.info("[FreeSearch] Found %d results", len(leads))
        return leads

    def _scrape_google_maps_html(self, city: str, category: str, limit: int) -> list[dict]:
        """
        Light HTML scrape of Google Maps search page.
        Google heavily obfuscates this, so results are minimal — just enough
        to demonstrate the pipeline without API keys.
        """
        if limit <= 0:
            return []

        query = urllib.parse.quote_plus(f"{category} {city}" if category else city)
        url   = f"{self.MAPS_URL}{query}/"
        leads = []

        try:
            resp = requests.get(url, headers=self.HEADERS, timeout=config.REQUEST_TIMEOUT)
            # Google Maps renders via JS, so static HTML contains very little.
            # We log a warning and return empty — Playwright (scraper.py) handles JS pages.
            if "consent.google" in resp.url:
                logger.warning("[FreeSearch] Google consent wall hit — skipping Maps HTML.")
                return []

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "lxml")

            # Attempt to find any JSON-LD structured data blocks
            for script in soup.find_all("script", type="application/ld+json"):
                import json
                try:
                    obj = json.loads(script.string or "")
                    if obj.get("@type") in ("LocalBusiness", "Organization"):
                        lead = _empty_lead(city, category or obj.get("@type", "Business"))
                        lead["Business Name"] = obj.get("name", "")
                        lead["Address"]       = obj.get("address", {}).get("streetAddress", "")
                        lead["Phone Number"]  = obj.get("telephone", "")
                        lead["Website"]       = obj.get("url", "")
                        lead["Source URL"]    = url
                        leads.append(lead)
                        if len(leads) >= limit:
                            break
                except Exception:
                    continue

        except Exception as exc:
            logger.warning("[FreeSearch] Google Maps HTML scrape failed: %s", exc)

        return leads


# ─────────────────────────────────────────────────────────────
# Public factory
# ─────────────────────────────────────────────────────────────

def get_leads(
    city: str,
    category: str = "",
    max_results: int = config.MAX_RESULTS_PER_CITY,
) -> list[dict]:
    """
    Entry point — auto-selects the best available search strategy.

    Args:
        city:        Target city name (e.g., "Noida").
        category:    Business type filter (e.g., "Schools"). Optional.
        max_results: Maximum number of raw leads to return (before dedup/cleaning).

    Returns:
        List of lead dicts matching config.CSV_COLUMNS.
    """
    if config.GOOGLE_PLACES_API_KEY:
        searcher = GooglePlacesSearcher(config.GOOGLE_PLACES_API_KEY)
        return searcher.search(city, category, max_results)

    if config.SERPAPI_KEY:
        searcher = SerpAPISearcher(config.SERPAPI_KEY)
        return searcher.search(city, category, max_results)

    logger.warning(
        "No API keys found. Using free fallback — results will be limited. "
        "Set GOOGLE_PLACES_API_KEY or SERPAPI_KEY in .env for full results."
    )
    searcher = FreeSearcher()
    return searcher.search(city, category, max_results)
