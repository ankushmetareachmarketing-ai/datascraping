"""
main.py — Lead generation pipeline orchestrator.

Can be run as a CLI tool or imported by the Streamlit UI.

CLI Usage:
  python main.py --cities "Delhi" "Noida" "Gurgaon" --category "Schools"
  python main.py --cities "Mumbai" --max-results 50 --no-scrape
"""

import argparse
import logging
import sys
from typing import Optional

import pandas as pd

import config
from maps_search   import get_leads
from scraper       import scrape_leads
from data_cleaner  import clean_leads, get_stats
from storage       import save_to_csv, save_to_sheets
from targeting     import (
    get_search_terms, enrich_leads_with_targeting,
    get_all_labels, get_tier_badge,
)

# ─────────────────────────────────────────────────────────────
# Logging setup
# ─────────────────────────────────────────────────────────────

logging.basicConfig(
    level   = getattr(logging, config.LOG_LEVEL, logging.INFO),
    format  = "%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt = "%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Core pipeline
# ─────────────────────────────────────────────────────────────

def run_pipeline(
    city: str,
    category: str          = "",
    max_results: int        = config.MAX_RESULTS_PER_CITY,
    enable_scraping: bool   = True,
    save_csv: bool          = True,
    save_sheets: bool       = False,
    progress_callback       = None,
) -> tuple[pd.DataFrame, str]:
    """
    Full lead-generation pipeline for a single city.

    Steps:
      1. Discover businesses via maps_search
      2. Optionally scrape websites for emails/phones
      3. Clean and deduplicate
      4. Save to CSV and/or Google Sheets

    Args:
        city:              Target city (required).
        category:          Business category filter (optional).
        max_results:       Max raw results before cleaning.
        enable_scraping:   Whether to scrape websites for contact info.
        save_csv:          Save output to CSV.
        save_sheets:       Upload to Google Sheets.
        progress_callback: Optional callable(step: str, pct: float) for UI.

    Returns:
        (cleaned_df, csv_filepath_or_empty_string)
    """

    def _progress(step: str, pct: float):
        logger.info("[%.0f%%] %s", pct * 100, step)
        if progress_callback:
            progress_callback(step, pct)

    # ── Step 1: Business Discovery ─────────────────────────
    _progress(f"Searching for '{category or 'businesses'}' in {city}…", 0.05)

    # Use smart search keywords if category is a known target
    search_terms = get_search_terms(category) if category else [category]
    raw_leads: list[dict] = []
    for term in search_terms:
        batch = get_leads(city, term, max(10, max_results // len(search_terms)))
        # Tag category label correctly
        for lead in batch:
            lead["Category"] = category or lead.get("Category", "")
        raw_leads.extend(batch)
        if len(raw_leads) >= max_results:
            raw_leads = raw_leads[:max_results]
            break

    if not raw_leads:
        logger.warning("No businesses found for city='%s' category='%s'.", city, category)
        empty_df = pd.DataFrame(columns=config.CSV_COLUMNS)
        return empty_df, ""

    _progress(f"Found {len(raw_leads)} raw businesses. Cleaning…", 0.30)

    # ── Step 2: Website Scraping ───────────────────────────
    if enable_scraping:
        websites = [l for l in raw_leads if l.get("Website")]
        _progress(
            f"Scraping {len(websites)} websites for email/phone…", 0.35
        )

        def _scrape_progress(current, total):
            pct = 0.35 + 0.50 * (current / total)
            _progress(f"Scraping website {current}/{total}…", pct)

        raw_leads = scrape_leads(raw_leads, _scrape_progress)
    else:
        _progress("Skipping website scraping.", 0.85)

    # ── Step 2.5: Targeting enrichment ────────────────────
    _progress("Tagging leads with services needed & lead tier…", 0.87)
    raw_leads = enrich_leads_with_targeting(raw_leads)

    # ── Step 3: Clean & Deduplicate ────────────────────────
    _progress("Cleaning and deduplicating leads…", 0.88)
    cleaned_df = clean_leads(raw_leads)

    stats = get_stats(cleaned_df)
    logger.info(
        "Pipeline stats for %s/%s: total=%d, with_email=%d, with_phone=%d, complete=%d",
        city, category or "all",
        stats["total"], stats["with_email"], stats["with_phone"], stats["fully_complete"],
    )

    # ── Step 4: Persist ────────────────────────────────────
    csv_path = ""

    if save_csv and not cleaned_df.empty:
        _progress("Saving CSV…", 0.93)
        csv_path = save_to_csv(cleaned_df, city, category)

    if save_sheets and not cleaned_df.empty:
        _progress("Uploading to Google Sheets…", 0.97)
        try:
            sheets_url = save_to_sheets(cleaned_df, city, category)
            logger.info("Google Sheets URL: %s", sheets_url)
        except Exception as exc:
            logger.error("Google Sheets upload failed: %s", exc)

    _progress("Done.", 1.0)
    return cleaned_df, csv_path


# ─────────────────────────────────────────────────────────────
# Multi-city automation
# ─────────────────────────────────────────────────────────────

def run_multi_city(
    cities: list[str],
    category: str        = "",
    max_results: int     = config.MAX_RESULTS_PER_CITY,
    enable_scraping: bool = True,
    save_csv: bool        = True,
    save_sheets: bool     = False,
) -> dict[str, pd.DataFrame]:
    """
    Run the pipeline for multiple cities sequentially.

    Returns:
        Dict mapping city name → cleaned DataFrame.
    """
    results = {}
    total   = len(cities)

    for i, city in enumerate(cities, 1):
        logger.info("─── [%d/%d] Processing city: %s ───", i, total, city)
        df, csv_path = run_pipeline(
            city            = city,
            category        = category,
            max_results     = max_results,
            enable_scraping = enable_scraping,
            save_csv        = save_csv,
            save_sheets     = save_sheets,
        )
        results[city] = df
        if csv_path:
            logger.info("Saved: %s", csv_path)

    return results


# ─────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────

def _cli():
    parser = argparse.ArgumentParser(
        description="Lead Agent — AI-powered business lead generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --cities Delhi --category "Digital Marketing Agencies"
  python main.py --cities Delhi Noida Gurgaon --category Schools
  python main.py --cities Mumbai --max-results 50 --no-scrape
  python main.py --cities Chennai --sheets
        """
    )
    parser.add_argument(
        "--cities", nargs="+", required=True,
        metavar="CITY",
        help="One or more city names (e.g. --cities Delhi Noida Gurgaon)"
    )
    parser.add_argument(
        "--category", default="",
        help="Business category filter (e.g. Schools, Restaurants, Gyms)"
    )
    parser.add_argument(
        "--max-results", type=int, default=config.MAX_RESULTS_PER_CITY,
        help=f"Max raw results per city (default: {config.MAX_RESULTS_PER_CITY})"
    )
    parser.add_argument(
        "--no-scrape", action="store_true",
        help="Skip website scraping (faster, fewer contacts)"
    )
    parser.add_argument(
        "--sheets", action="store_true",
        help="Upload results to Google Sheets"
    )

    args = parser.parse_args()

    if len(args.cities) == 1:
        df, path = run_pipeline(
            city            = args.cities[0],
            category        = args.category,
            max_results     = args.max_results,
            enable_scraping = not args.no_scrape,
            save_csv        = True,
            save_sheets     = args.sheets,
        )
        print(f"\n✅  Done! {len(df)} leads saved to: {path}")
    else:
        results = run_multi_city(
            cities          = args.cities,
            category        = args.category,
            max_results     = args.max_results,
            enable_scraping = not args.no_scrape,
            save_csv        = True,
            save_sheets     = args.sheets,
        )
        total = sum(len(df) for df in results.values())
        print(f"\n✅  Done! {total} total leads across {len(results)} cities.")


if __name__ == "__main__":
    _cli()
