"""
ui.py — Lead Agent Streamlit Dashboard with Smart Targeting.

Run with:
    streamlit run ui.py
"""

import logging
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))

import config
from data_cleaner import get_stats
from main         import run_pipeline
from storage      import list_saved_files, load_csv
from targeting    import (
    CATEGORIES, ALL_SERVICES, get_tier_badge,
    BULK_SMS, WHATSAPP, SEO, WEB_DESIGN, IVR,
    get_by_service, get_all_labels, get_category,
)

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title = "Lead Agent 🎯",
    page_icon  = "🎯",
    layout     = "wide",
    initial_sidebar_state = "expanded",
)

# ─────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────

st.markdown("""
<style>
div[data-testid="metric-container"] {
    background:linear-gradient(135deg,#1e3a5f,#2d5a8e);
    border-radius:12px; padding:16px;
    border:1px solid #3a7bd5; color:white;
}
div[data-testid="metric-container"] label{color:#a8d4f5!important;font-size:.8rem!important;}
div[data-testid="metric-container"] div[data-testid="stMetricValue"]{
    color:white!important;font-size:1.9rem!important;font-weight:700!important;}
section[data-testid="stSidebar"]{background:linear-gradient(180deg,#0d1b2a,#1a2e44);}
.main-header{
    background:linear-gradient(135deg,#0d1b2a,#1a3a5c);
    padding:1.5rem 2rem;border-radius:16px;margin-bottom:1.2rem;
    border:1px solid #2d5a8e;}
.tier-A{color:#ff6b6b;font-weight:700;}
.tier-B{color:#ffd93d;font-weight:700;}
.tier-C{color:#74b9ff;font-weight:700;}
.svc-badge{
    display:inline-block;border-radius:20px;padding:3px 10px;
    font-size:.7rem;margin:2px;font-weight:600;}
.svc-sms{background:#1a3a1a;color:#6fcf97;border:1px solid #27ae60;}
.svc-wa{background:#1a3a20;color:#25d366;border:1px solid #25d366;}
.svc-seo{background:#1a2a3a;color:#56ccf2;border:1px solid #2980b9;}
.svc-web{background:#2a1a3a;color:#bb86fc;border:1px solid #7b2ff7;}
.svc-ivr{background:#3a2a1a;color:#f2994a;border:1px solid #e67e22;}
.pitch-box{
    background:#0d1b2a;border-left:3px solid #3a7bd5;
    border-radius:0 8px 8px 0;padding:10px 14px;
    font-size:.85rem;color:#c8d8e8;margin:4px 0;}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

SERVICE_CSS = {
    BULK_SMS:"svc-sms", WHATSAPP:"svc-wa",
    SEO:"svc-seo", WEB_DESIGN:"svc-web", IVR:"svc-ivr",
}
SERVICE_ICONS = {BULK_SMS:"📱",WHATSAPP:"💬",SEO:"🔍",WEB_DESIGN:"🌐",IVR:"📞"}

def _svc_badge(svc):
    css = SERVICE_CSS.get(svc,"svc-sms")
    icon = SERVICE_ICONS.get(svc,"")
    return f'<span class="svc-badge {css}">{icon} {svc}</span>'

def _tier_label(tier):
    return {"A":'<span class="tier-A">🔥 Hot</span>',
            "B":'<span class="tier-B">🟡 Warm</span>',
            "C":'<span class="tier-C">🔵 Cold</span>'}.get(tier, tier)


# ─────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 🎯 Lead Agent")
    st.caption("AI-powered B2B lead generation for digital marketing agencies")
    st.divider()
    st.markdown("### ⚙️ Settings")
    max_results     = st.slider("Max results per city", 10, 200, 50, 10)
    enable_scraping = st.toggle("🔍 Scrape websites", True)
    save_to_sheets  = st.toggle("📊 Google Sheets", False)
    st.divider()
    st.markdown("### 🔑 API Status")
    if config.GOOGLE_PLACES_API_KEY:
        st.success("✅ Google Places API")
    elif config.SERPAPI_KEY:
        st.warning("⚠️ SerpAPI (fallback)")
    else:
        st.error("❌ Free mode — limited results")
    st.divider()
    st.markdown("### 📂 Saved Files")
    saved = list_saved_files()
    if saved:
        for f in saved[-5:]:
            fname = Path(f).name
            if st.button(f"📄 {fname}", key=f"load_{f}", width="stretch"):
                st.session_state["loaded_df"]   = load_csv(f)
                st.session_state["loaded_file"] = fname
    else:
        st.caption("No saved files yet.")


# ─────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────

st.markdown("""
<div class="main-header">
  <h1 style="color:white;margin:0;font-size:2rem;">🎯 Lead Agent</h1>
  <p style="color:#a8d4f5;margin:.4rem 0 .8rem 0;">
    AI-powered lead generation &nbsp;·&nbsp; Smart business targeting for digital agencies
  </p>
  <span class="svc-badge svc-sms">📱 Bulk SMS</span>
  <span class="svc-badge svc-wa">💬 WhatsApp API</span>
  <span class="svc-badge svc-seo">🔍 Digital Marketing / SEO</span>
  <span class="svc-badge svc-web">🌐 Web Design</span>
  <span class="svc-badge svc-ivr">📞 IVR</span>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# Main tabs
# ─────────────────────────────────────────────────────────────

tab_collect, tab_browse, tab_service = st.tabs([
    "🚀 Collect Leads",
    "📂 Browse Categories",
    "🔍 Filter by Service",
])


# ══════════════════════════════════════════════════════════════
# TAB 1 — Collect Leads
# ══════════════════════════════════════════════════════════════

with tab_collect:
    st.markdown("### Enter your target")

    col_city, col_cat = st.columns([3, 4])

    with col_city:
        cities_input = st.text_input(
            "🏙️ Cities (comma-separated)",
            placeholder="Delhi, Noida, Gurgaon",
        )
        # Quick city presets
        st.markdown("**Quick presets:**")
        qc1, qc2 = st.columns(2)
        if qc1.button("📍 Delhi NCR", width="stretch"):
            cities_input = "Delhi, Noida, Gurgaon, Faridabad"
        if qc2.button("📍 Mumbai Metro", width="stretch"):
            cities_input = "Mumbai, Pune, Thane"
        qc3, qc4 = st.columns(2)
        if qc3.button("📍 South India", width="stretch"):
            cities_input = "Bangalore, Chennai, Hyderabad"
        if qc4.button("📍 All Metros", width="stretch"):
            cities_input = "Delhi, Mumbai, Bangalore, Chennai, Hyderabad, Kolkata"

    with col_cat:
        all_labels = get_all_labels()
        category_selected = st.selectbox(
            "🏢 Business Category",
            ["— Select a category —"] + all_labels,
        )
        if category_selected == "— Select a category —":
            category_selected = ""

        # Show category info card
        if category_selected:
            cat_obj = get_category(category_selected)
            if cat_obj:
                svcs_html = " ".join(_svc_badge(s) for s in cat_obj.services)
                st.markdown(
                    f'<div style="background:#111e2e;border:1px solid #253d57;'
                    f'border-radius:10px;padding:12px;margin-top:6px">'
                    f'<div style="font-size:.9rem;color:#a8d4f5;margin-bottom:6px">'
                    f'{cat_obj.icon} <b>{cat_obj.label}</b> &nbsp; {_tier_label(cat_obj.tier)}</div>'
                    f'<div style="font-size:.8rem;color:#7a9cbf;margin-bottom:8px">{cat_obj.description}</div>'
                    f'{svcs_html}'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        custom_cat = st.text_input(
            "✏️ Or type a custom category",
            placeholder="e.g. Florists, Pet Shops…",
        )
        if custom_cat:
            category_selected = custom_cat

    st.markdown("<br>", unsafe_allow_html=True)
    run_btn = st.button("🚀 Collect Leads", width="stretch", type="primary")

    # ── Pipeline execution ─────────────────────────────────
    if run_btn:
        if not cities_input.strip():
            st.error("Please enter at least one city.")
            st.stop()

        cities   = [c.strip() for c in cities_input.split(",") if c.strip()]
        category = category_selected.strip()

        st.divider()
        st.markdown(f"### ⏳ Running pipeline for **{len(cities)}** city(ies)…")
        progress_bar = st.progress(0, text="Starting…")
        status_text  = st.empty()
        results: dict[str, pd.DataFrame] = {}

        def _prog(step, pct):
            progress_bar.progress(min(pct, 1.0), text=step)
            status_text.info(f"⏳ {step}")

        for i, city in enumerate(cities):
            base = i / len(cities)
            top  = (i + 1) / len(cities)
            def _scaled(step, pct, b=base, t=top, c=city):
                _prog(f"[{c}] {step}", b + pct * (t - b))

            df, _ = run_pipeline(
                city=city, category=category,
                max_results=max_results,
                enable_scraping=enable_scraping,
                save_csv=True, save_sheets=save_to_sheets,
                progress_callback=_scaled,
            )
            results[city] = df

        progress_bar.progress(1.0, text="✅ Done!")
        status_text.empty()
        st.session_state["results_by_city"] = results
        st.session_state["loaded_df"] = None

    # ── Results ────────────────────────────────────────────
    def _show_results(results_by_city):
        all_dfs = [df for df in results_by_city.values() if df is not None and not df.empty]
        if not all_dfs:
            st.warning("No leads found. Try a different city/category, or add API keys.")
            return

        combined = pd.concat(all_dfs, ignore_index=True)
        stats    = get_stats(combined)

        st.markdown("### 📊 Results Summary")
        m1,m2,m3,m4,m5,m6 = st.columns(6)
        m1.metric("Total Leads",   stats["total"])
        m2.metric("With Email",    stats["with_email"])
        m3.metric("With Phone",    stats["with_phone"])
        m4.metric("With Website",  stats["with_website"])
        m5.metric("Email + Phone", stats["fully_complete"])
        if "Lead Tier" in combined.columns:
            m6.metric("🔥 Hot Leads", int((combined["Lead Tier"]=="A").sum()))

        # Tier progress bars
        if "Lead Tier" in combined.columns:
            n = max(len(combined), 1)
            tc1,tc2,tc3 = st.columns(3)
            tc1.progress(int((combined["Lead Tier"]=="A").sum())/n,
                         text=f"🔥 Hot ({int((combined['Lead Tier']=='A').sum())})")
            tc2.progress(int((combined["Lead Tier"]=="B").sum())/n,
                         text=f"🟡 Warm ({int((combined['Lead Tier']=='B').sum())})")
            tc3.progress(int((combined["Lead Tier"]=="C").sum())/n,
                         text=f"🔵 Cold ({int((combined['Lead Tier']=='C').sum())})")

        # City tabs
        st.markdown("### 📋 Leads")
        city_names = list(results_by_city.keys())
        tab_names = (["🌐 All Cities"] + city_names) if len(city_names)>1 else city_names
        df_list   = ([combined] + [results_by_city[c] for c in city_names]) if len(city_names)>1 else [results_by_city[city_names[0]]]

        for tab, df, lbl in zip(st.tabs(tab_names), df_list, tab_names):
            with tab:
                if df is None or df.empty:
                    st.warning("No data.")
                    continue
                fc1,fc2,fc3,fc4 = st.columns(4)
                f_email  = fc1.checkbox("📧 Has email",  key=f"em_{lbl}")
                f_phone  = fc2.checkbox("📞 Has phone",  key=f"ph_{lbl}")
                f_hot    = fc3.checkbox("🔥 Hot only",   key=f"hot_{lbl}")
                f_search = fc4.text_input("🔎 Search", key=f"srch_{lbl}")
                fdf = df.copy()
                if f_email  and "Email"        in fdf.columns: fdf = fdf[fdf["Email"]!=""]
                if f_phone  and "Phone Number" in fdf.columns: fdf = fdf[fdf["Phone Number"]!=""]
                if f_hot    and "Lead Tier"    in fdf.columns: fdf = fdf[fdf["Lead Tier"]=="A"]
                if f_search and "Business Name" in fdf.columns:
                    fdf = fdf[fdf["Business Name"].str.contains(f_search,case=False,na=False)]
                st.caption(f"Showing **{len(fdf)}** of **{len(df)}** leads")
                display_cols = [c for c in fdf.columns if c != "Sales Pitch"]
                st.dataframe(fdf[display_cols], width="stretch", height=420)
                csv_bytes = fdf.to_csv(index=False,encoding="utf-8-sig").encode("utf-8-sig")
                st.download_button(
                    f"⬇️ Download {lbl} CSV", csv_bytes,
                    f"leads_{lbl.lower().replace(' ','_')}.csv", "text/csv",
                    width="stretch",
                )

    if "results_by_city" in st.session_state:
        _show_results(st.session_state["results_by_city"])
    elif st.session_state.get("loaded_df") is not None:
        fname = st.session_state.get("loaded_file","File")
        st.markdown(f"### 📂 {fname}")
        df = st.session_state["loaded_df"]
        st.dataframe(df, width="stretch")
        st.download_button("⬇️ Download",
            df.to_csv(index=False,encoding="utf-8-sig").encode("utf-8-sig"),
            fname, "text/csv")
    else:
        st.divider()
        st.markdown("#### 💡 How it works")
        c1,c2,c3,c4 = st.columns(4)
        c1.markdown("**1️⃣ Search**\nDiscovers businesses via Google Maps / SerpAPI / free fallback")
        c2.markdown("**2️⃣ Tag**\nMatches businesses to services they need + lead tier (Hot/Warm/Cold)")
        c3.markdown("**3️⃣ Scrape**\nVisits websites to extract emails & phone numbers")
        c4.markdown("**4️⃣ Export**\nSaves to timestamped CSV + optional Google Sheets")
        st.info("💡 Add `GOOGLE_PLACES_API_KEY` or `SERPAPI_KEY` to `.env` for full results.", icon="💡")


# ══════════════════════════════════════════════════════════════
# TAB 2 — Browse Categories
# ══════════════════════════════════════════════════════════════

with tab_browse:
    st.markdown(f"### 📂 All {len(CATEGORIES)} Target Business Categories")
    st.caption("Every category is pre-mapped to the services they need + individual sales pitches.")

    bc1, bc2 = st.columns([3,2])
    tier_filter = bc1.multiselect(
        "Filter by tier",
        ["🔥 Hot (A)","🟡 Warm (B)","🔵 Cold (C)"],
        default=["🔥 Hot (A)","🟡 Warm (B)","🔵 Cold (C)"],
    )
    svc_filter = bc2.multiselect("Filter by service", ALL_SERVICES, default=[], placeholder="All services")
    tier_map = {"🔥 Hot (A)":"A","🟡 Warm (B)":"B","🔵 Cold (C)":"C"}
    active_tiers = [tier_map[t] for t in tier_filter]

    for cat in CATEGORIES:
        if cat.tier not in active_tiers: continue
        if svc_filter and not any(s in cat.services for s in svc_filter): continue
        svcs_html = " ".join(_svc_badge(s) for s in cat.services)
        with st.expander(f"{cat.icon}  **{cat.label}**  ·  {get_tier_badge(cat.tier)}", expanded=False):
            st.markdown(
                f'<p style="color:#a8d4f5;font-size:.88rem;margin:.3rem 0 .6rem 0">{cat.description}</p>',
                unsafe_allow_html=True)
            st.markdown(f"**Services needed:** {svcs_html}", unsafe_allow_html=True)
            st.markdown("**Sales pitches:**")
            for svc, pitch in cat.pitch.items():
                st.markdown(
                    f'<div class="pitch-box"><b>{SERVICE_ICONS.get(svc,"")} {svc}:</b> {pitch}</div>',
                    unsafe_allow_html=True)
            kw_html = " ".join(
                f'<span style="background:#1a2e44;color:#74b9ff;border-radius:12px;'
                f'padding:2px 10px;font-size:.75rem;margin:2px">{kw}</span>'
                for kw in cat.search_keywords)
            st.markdown(f"**Search keywords:** {kw_html}", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# TAB 3 — Filter by Service
# ══════════════════════════════════════════════════════════════

with tab_service:
    st.markdown("### 🔍 Which businesses need each service?")
    st.caption("Use this to plan which service to pitch to which sector.")

    for svc in ALL_SERVICES:
        icon = SERVICE_ICONS.get(svc,"")
        cats = get_by_service(svc)
        hot  = [c for c in cats if c.tier=="A"]
        warm = [c for c in cats if c.tier=="B"]
        cold = [c for c in cats if c.tier=="C"]
        with st.expander(f"{icon} **{svc}** — {len(cats)} business types", expanded=False):
            for grp_label, grp in [("🔥 Hot (Tier A)", hot),("🟡 Warm (Tier B)", warm),("🔵 Cold (Tier C)", cold)]:
                if not grp: continue
                st.markdown(f"**{grp_label}**")
                rows = [{"Category": f"{c.icon} {c.label}", "Why they need it": c.pitch.get(svc,"")} for c in grp]
                st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
