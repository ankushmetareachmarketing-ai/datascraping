# 🎯 Lead Agent — AI-Powered Lead Generation System

Automatically discover businesses in any city and extract their contact information
(website, email, phone, address) for digital marketing campaigns.

---

## ✨ Features

| Feature | Details |
|---|---|
| **Business Discovery** | Google Places API → SerpAPI → Free fallback |
| **Website Scraping** | requests + BeautifulSoup + Playwright (JS sites) |
| **Contact Extraction** | Regex email/phone extraction with validation |
| **Data Cleaning** | Deduplication, validation, completeness scoring |
| **Multi-city** | Process Delhi, Noida, Gurgaon in one command |
| **Export** | CSV + optional Google Sheets upload |
| **Dashboard** | Streamlit UI with filters, search, download |

---

## 🗂️ Project Structure

```
lead-agent/
├── main.py            # Pipeline orchestrator + CLI entry point
├── ui.py              # Streamlit dashboard
├── maps_search.py     # Business discovery (Google Places / SerpAPI / free)
├── scraper.py         # Website scraping (requests + Playwright)
├── email_extractor.py # Email + phone regex extraction
├── data_cleaner.py    # Deduplication and validation (pandas)
├── storage.py         # CSV + Google Sheets export
├── config.py          # Centralised config from .env
├── requirements.txt   # Python dependencies
├── .env.example       # Environment variable template
└── output/            # Generated CSV files (auto-created)
```

---

## ⚡ Quick Start

### 1. Clone / download the project

```bash
cd lead-agent
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
source venv/bin/activate      # Linux/macOS
venv\Scripts\activate         # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Playwright browsers (optional, for JS-heavy websites)

```bash
playwright install chromium
```

### 5. Configure API keys

```bash
cp .env.example .env
# Edit .env and add your API keys
```

See **API Keys Setup** below for how to get free keys.

### 6. Run the Streamlit dashboard

```bash
streamlit run ui.py
```

Then open http://localhost:8501 in your browser.

---

## 🖥️ CLI Usage

```bash
# Single city
python main.py --cities Delhi --category "Schools"

# Multiple cities → separate CSVs per city
python main.py --cities "Delhi" "Noida" "Gurgaon" --category "Restaurants"

# No API keys (free mode, limited results)
python main.py --cities Mumbai --no-scrape

# Upload to Google Sheets after collection
python main.py --cities Chennai --category "Hospitals" --sheets

# Increase result count
python main.py --cities Bangalore --max-results 100
```

---

## 🔑 API Keys Setup

### Option A — Google Places API (Recommended, ~$17 free credit/month)

1. Go to https://console.cloud.google.com
2. Create a new project
3. Enable: **Places API** and **Maps JavaScript API**
4. Create an API key: **APIs & Services → Credentials → Create Credentials**
5. Add to `.env`:
   ```
   GOOGLE_PLACES_API_KEY=AIzaSy...your_key_here
   ```

### Option B — SerpAPI (100 free searches/month)

1. Sign up at https://serpapi.com
2. Copy your API key from the dashboard
3. Add to `.env`:
   ```
   SERPAPI_KEY=your_serpapi_key_here
   ```

### Option C — Free mode (no API keys)

The system will use DuckDuckGo and public HTML scraping.
Results will be limited (~10-20 per city) but completely free.

---

## 📊 Google Sheets Setup (Optional)

1. Go to https://console.cloud.google.com
2. Enable the **Google Sheets API** and **Google Drive API**
3. Create a Service Account: **IAM & Admin → Service Accounts → Create**
4. Download the JSON key and save to `credentials/google_service_account.json`
5. Share your target Google Sheet with the service account email (Editor access)
6. Copy the spreadsheet ID from the URL:
   `https://docs.google.com/spreadsheets/d/`**`THIS_PART`**`/edit`
7. Add to `.env`:
   ```
   GOOGLE_SERVICE_ACCOUNT_JSON=credentials/google_service_account.json
   GOOGLE_SPREADSHEET_ID=your_spreadsheet_id
   ```
8. Enable in the UI toggle or use `--sheets` flag

---

## 📈 Output Format

Each CSV / Sheet contains these columns:

| Column | Description |
|---|---|
| Business Name | Company name |
| Category | Business type |
| City | Target city |
| Address | Physical address |
| Phone Number | 10-digit mobile or landline |
| Website | Full URL |
| Email | Validated email address |
| Source URL | Google Maps link |

Results are sorted by **completeness score** (most complete leads first).

---

## 🚀 Scaling to Thousands of Leads

### 1. Use Google Places API pagination
The Google Places API returns 60 results per query (3 pages × 20).
To get more, use multiple category variants:
```python
categories = ["schools", "primary schools", "secondary schools", "private schools"]
for cat in categories:
    run_pipeline("Delhi", cat)
```

### 2. Run cities in parallel with async
Replace `run_multi_city()` sequential loop with `asyncio.gather()`:
```python
import asyncio
from concurrent.futures import ProcessPoolExecutor

with ProcessPoolExecutor(max_workers=4) as pool:
    futures = [pool.submit(run_pipeline, city, category) for city in cities]
```

### 3. Use a proxy pool for scraping
To avoid IP blocks on website scraping:
```bash
pip install rotating-proxies
```
Then pass proxies into the `requests.Session` in `scraper.py`.

### 4. Add a job queue for massive scale
Use **Celery + Redis** for distributed processing:
```python
# tasks.py
from celery import Celery
app = Celery("lead-agent", broker="redis://localhost:6379/0")

@app.task
def collect_city(city, category):
    return run_pipeline(city, category)
```
Dispatch thousands of jobs:
```python
for city in city_list:
    collect_city.delay(city, "Schools")
```

### 5. Store in PostgreSQL for deduplication at scale
Replace CSV storage with SQLAlchemy + PostgreSQL:
```python
from sqlalchemy import create_engine
df.to_sql("leads", engine, if_exists="append", index=False)
```
Add a UNIQUE constraint on `(Business Name, City)` for DB-level deduplication.

### 6. Rate limiting and retry strategy
The `tenacity` library is already configured in `maps_search.py` and `scraper.py`.
Tune `MAX_WORKERS` in `.env` to balance speed vs. IP block risk.

---

## 🔧 Troubleshooting

| Issue | Solution |
|---|---|
| `No results found` | Check API keys in `.env`; try free mode first |
| `Playwright not found` | Run `playwright install chromium` |
| `Google Sheets 403` | Share sheet with service account email |
| `Rate limited` | Reduce `MAX_WORKERS` in `.env` (try 2-3) |
| `Empty emails` | Many sites use contact forms; this is expected |

---

## 📦 Dependencies

```
streamlit       — Dashboard UI
pandas          — Data cleaning and CSV export
requests        — HTTP scraping
beautifulsoup4  — HTML parsing
playwright      — JS-rendered page scraping
tenacity        — Retry logic
python-dotenv   — Environment variable loading
gspread         — Google Sheets integration (optional)
phonenumbers    — Phone validation (optional)
```

---

## 📄 License

MIT — free to use, modify, and distribute.
