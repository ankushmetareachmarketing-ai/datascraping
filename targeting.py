"""
targeting.py — Smart business category targeting system.

Maps every business category to:
  • The digital services they most likely need
  • Google Places / SerpAPI search keywords
  • Lead priority tier (A/B/C)
  • Why they need each service (sales pitch hint)
"""

from dataclasses import dataclass, field
from typing import Optional

# ─────────────────────────────────────────────────────────────
# Service flags
# ─────────────────────────────────────────────────────────────

BULK_SMS    = "Bulk SMS"
WHATSAPP    = "WhatsApp API"
SEO         = "Digital Marketing / SEO"
WEB_DESIGN  = "Web Design"
IVR         = "IVR"


# ─────────────────────────────────────────────────────────────
# Data model
# ─────────────────────────────────────────────────────────────

@dataclass
class TargetCategory:
    label: str                          # Display name in UI
    icon: str                           # Emoji icon
    tier: str                           # A = hottest, B = warm, C = cold
    services: list[str]                 # Services they need
    search_keywords: list[str]          # Google Places search terms
    pitch: dict[str, str]               # service → 1-line sales pitch
    description: str = ""              # Short category description


# ─────────────────────────────────────────────────────────────
# Master category registry
# ─────────────────────────────────────────────────────────────

CATEGORIES: list[TargetCategory] = [

    # ── Retail ───────────────────────────────────────────────
    TargetCategory(
        label    = "Retail Shops & Showrooms",
        icon     = "🛒",
        tier     = "A",
        services = [BULK_SMS, WHATSAPP, SEO, WEB_DESIGN, IVR],
        search_keywords = [
            "retail shop", "showroom", "clothing store",
            "electronics store", "furniture showroom", "supermarket",
        ],
        pitch = {
            BULK_SMS:   "Send offer alerts & seasonal sale SMS to lakhs of customers instantly.",
            WHATSAPP:   "Share product catalogues, new arrivals & order updates on WhatsApp.",
            SEO:        "Rank on Google for 'best shop in [city]' and drive footfall.",
            WEB_DESIGN: "Online store / catalogue website to capture online buyers.",
            IVR:        "Never miss a customer call — auto-reply with store timings & offers.",
        },
        description = "High-volume walk-in customer base — perfect for SMS & WhatsApp promotions.",
    ),

    # ── Healthcare ────────────────────────────────────────────
    TargetCategory(
        label    = "Hospitals, Clinics & Doctors",
        icon     = "🏥",
        tier     = "A",
        services = [WHATSAPP, IVR, SEO, WEB_DESIGN, BULK_SMS],
        search_keywords = [
            "hospital", "clinic", "doctor", "medical centre",
            "nursing home", "diagnostic centre", "dental clinic",
            "eye hospital", "physiotherapy clinic",
        ],
        pitch = {
            WHATSAPP:   "Send appointment reminders, lab reports & health tips on WhatsApp.",
            IVR:        "24×7 automated appointment booking and doctor availability IVR.",
            SEO:        "Rank for 'best doctor in [city]' — patients search Google first.",
            WEB_DESIGN: "Professional website with online appointment booking.",
            BULK_SMS:   "SMS reminders for follow-ups, health camps & vaccination drives.",
        },
        description = "High appointment volume + regulatory need for patient communication.",
    ),

    # ── Education ─────────────────────────────────────────────
    TargetCategory(
        label    = "Schools, Colleges & Coaching",
        icon     = "🎓",
        tier     = "A",
        services = [BULK_SMS, WHATSAPP, IVR, SEO, WEB_DESIGN],
        search_keywords = [
            "school", "college", "coaching centre", "institute",
            "tuition", "academy", "university", "play school",
            "cbse school", "icse school", "engineering college",
        ],
        pitch = {
            BULK_SMS:   "Bulk SMS for exam alerts, PTM notices & fee reminders to all parents.",
            WHATSAPP:   "WhatsApp group broadcast for circulars, results & parent updates.",
            IVR:        "Automated attendance / fee due IVR calls to parents.",
            SEO:        "Rank for 'best school in [city]' during admission season.",
            WEB_DESIGN: "Admission enquiry website with online form & fee portal.",
        },
        description = "Large parent database — high ROI on bulk communication tools.",
    ),

    # ── Restaurants ──────────────────────────────────────────
    TargetCategory(
        label    = "Restaurants, Hotels & Salons",
        icon     = "🍽️",
        tier     = "A",
        services = [WHATSAPP, BULK_SMS, SEO, WEB_DESIGN, IVR],
        search_keywords = [
            "restaurant", "hotel", "salon", "spa", "cafe",
            "dhaba", "fast food", "bar restaurant", "beauty parlour",
            "banquet hall", "caterer",
        ],
        pitch = {
            WHATSAPP:   "Send daily specials, table booking confirmations & festive offers.",
            BULK_SMS:   "Weekend offer SMS drives repeat customers back to the outlet.",
            SEO:        "Rank on Google Maps so hungry customers find you first.",
            WEB_DESIGN: "Menu website with online table/slot booking.",
            IVR:        "Automated reservation IVR so no booking is ever missed.",
        },
        description = "Repeat customer business — loyalty & offer communication is key.",
    ),

    # ── E-commerce ────────────────────────────────────────────
    TargetCategory(
        label    = "E-commerce Businesses",
        icon     = "🛍️",
        tier     = "A",
        services = [WHATSAPP, SEO, BULK_SMS, WEB_DESIGN, IVR],
        search_keywords = [
            "ecommerce", "online store", "online shop",
            "online retailer", "dropshipping business",
        ],
        pitch = {
            WHATSAPP:   "Order confirmation, shipping updates & abandoned cart recovery on WhatsApp.",
            SEO:        "Drive organic traffic to product pages and reduce ad spend.",
            BULK_SMS:   "Flash sale & discount SMS blasts for instant revenue spikes.",
            WEB_DESIGN: "High-converting product pages and checkout UX redesign.",
            IVR:        "Order status IVR reduces support calls by 60%.",
        },
        description = "Digital-first businesses — every touchpoint is online.",
    ),

    # ── Cosmetics & Jewellery ─────────────────────────────────
    TargetCategory(
        label    = "Cosmetics & Jewellery Brands",
        icon     = "💍",
        tier     = "A",
        services = [WHATSAPP, SEO, WEB_DESIGN, BULK_SMS],
        search_keywords = [
            "jewellery shop", "cosmetics brand", "cosmetics store",
            "jewellers", "gold shop", "beauty brand",
            "makeup brand", "skincare brand",
        ],
        pitch = {
            WHATSAPP:   "Share new collection lookbooks, price lists & festive offers on WhatsApp.",
            SEO:        "Rank for high-intent searches like 'gold jewellery in [city]'.",
            WEB_DESIGN: "Elegant product catalogue / e-commerce site.",
            BULK_SMS:   "Festive season SMS (Diwali, Dhanteras, Wedding season) campaigns.",
        },
        description = "Visual, aspirational products — social & WhatsApp marketing is king.",
    ),

    # ── Consulting ────────────────────────────────────────────
    TargetCategory(
        label    = "Consulting Firms",
        icon     = "💼",
        tier     = "B",
        services = [SEO, WEB_DESIGN, WHATSAPP, IVR],
        search_keywords = [
            "consulting firm", "management consultant",
            "ca firm", "chartered accountant", "tax consultant",
            "business consultant", "hr consulting", "legal consultant",
            "lawyer", "advocate",
        ],
        pitch = {
            SEO:        "Rank for '[service] consultant in [city]' to generate inbound leads.",
            WEB_DESIGN: "Professional website builds credibility and captures enquiries.",
            WHATSAPP:   "Share proposals, documents & updates with clients on WhatsApp.",
            IVR:        "Automated call routing so clients always reach the right person.",
        },
        description = "High-ticket services — strong online presence directly drives revenue.",
    ),

    # ── Real Estate ───────────────────────────────────────────
    TargetCategory(
        label    = "Real Estate Agents & Builders",
        icon     = "🏘️",
        tier     = "A",
        services = [BULK_SMS, WHATSAPP, SEO, WEB_DESIGN, IVR],
        search_keywords = [
            "real estate agent", "property dealer", "builder",
            "developer", "property consultant", "housing society",
            "real estate broker", "plot seller",
        ],
        pitch = {
            BULK_SMS:   "Launch bulk SMS campaigns for new project launches to thousands of buyers.",
            WHATSAPP:   "Share property videos, floor plans & site visit confirmations on WhatsApp.",
            SEO:        "Rank for 'flats in [city]' and capture buyers at the research stage.",
            WEB_DESIGN: "Property listing website with virtual tour & enquiry forms.",
            IVR:        "Missed-call lead capture — buyer calls a number and gets a callback.",
        },
        description = "High-value, high-competition — digital marketing delivers measurable ROI.",
    ),

    # ── Automobile ────────────────────────────────────────────
    TargetCategory(
        label    = "Automobile Dealers & Service",
        icon     = "🚗",
        tier     = "A",
        services = [BULK_SMS, WHATSAPP, IVR, SEO, WEB_DESIGN],
        search_keywords = [
            "car showroom", "automobile dealer", "car dealer",
            "bike showroom", "two-wheeler dealer", "car service centre",
            "auto workshop", "car accessories shop",
        ],
        pitch = {
            BULK_SMS:   "Service due reminders & new model launch SMS to existing customers.",
            WHATSAPP:   "Share test-drive bookings, EMI offers & car photos on WhatsApp.",
            IVR:        "Automated service appointment booking IVR — no missed calls.",
            SEO:        "Rank for '[brand] dealer in [city]' to capture ready-to-buy leads.",
            WEB_DESIGN: "Showroom website with stock listing, EMI calculator & test drive form.",
        },
        description = "Repeat service customers + new buyers — both channels need digital touch.",
    ),

    # ── Construction ──────────────────────────────────────────
    TargetCategory(
        label    = "Construction & Contractors",
        icon     = "🏗️",
        tier     = "B",
        services = [SEO, WEB_DESIGN, WHATSAPP, BULK_SMS],
        search_keywords = [
            "construction company", "contractor", "civil contractor",
            "builder contractor", "interior contractor",
            "renovation company", "waterproofing company",
        ],
        pitch = {
            SEO:        "Rank for 'construction company in [city]' to win B2B tenders online.",
            WEB_DESIGN: "Project portfolio website to showcase past work and win contracts.",
            WHATSAPP:   "Share project updates, quotations & material specs on WhatsApp.",
            BULK_SMS:   "Reach architects & builders via targeted SMS for B2B leads.",
        },
        description = "B2B-heavy sector — website and SEO credibility wins large contracts.",
    ),

    # ── Gym & Fitness ─────────────────────────────────────────
    TargetCategory(
        label    = "Gym & Fitness Centres",
        icon     = "💪",
        tier     = "A",
        services = [BULK_SMS, WHATSAPP, SEO, WEB_DESIGN, IVR],
        search_keywords = [
            "gym", "fitness centre", "yoga studio", "crossfit",
            "zumba classes", "personal trainer", "sports club",
        ],
        pitch = {
            BULK_SMS:   "Membership renewal reminders & New Year offer SMS blasts.",
            WHATSAPP:   "Daily workout tips, diet plans & batch schedule on WhatsApp.",
            SEO:        "Rank for 'gym near me' — most gym searches happen on Google.",
            WEB_DESIGN: "Online membership form & batch booking website.",
            IVR:        "Automated trial class booking IVR to never miss a prospect call.",
        },
        description = "Seasonal spike business (Jan, June) — needs aggressive lead capture.",
    ),

    # ── Fashion ───────────────────────────────────────────────
    TargetCategory(
        label    = "Fashion & Apparel Brands",
        icon     = "👗",
        tier     = "B",
        services = [WHATSAPP, SEO, WEB_DESIGN, BULK_SMS],
        search_keywords = [
            "fashion brand", "clothing brand", "boutique",
            "garment shop", "designer studio", "apparel store",
            "ethnic wear", "kurta shop",
        ],
        pitch = {
            WHATSAPP:   "Share new collection lookbooks and sale alerts with customers.",
            SEO:        "Drive traffic for 'ethnic wear in [city]' or '[brand] online'.",
            WEB_DESIGN: "Shoppable catalogue website with lookbook & size guide.",
            BULK_SMS:   "End-of-season clearance SMS campaigns drive footfall fast.",
        },
        description = "Visual product, trend-driven — WhatsApp & Instagram are primary channels.",
    ),

    # ── Event Planners ────────────────────────────────────────
    TargetCategory(
        label    = "Event Planners & Management",
        icon     = "🎉",
        tier     = "B",
        services = [SEO, WHATSAPP, WEB_DESIGN, BULK_SMS, IVR],
        search_keywords = [
            "event planner", "event management company",
            "wedding planner", "birthday event planner",
            "corporate event company", "party organiser",
        ],
        pitch = {
            SEO:        "Rank for 'wedding planner in [city]' — brides search Google obsessively.",
            WHATSAPP:   "Share event portfolios, mood boards & vendor quotes on WhatsApp.",
            WEB_DESIGN: "Gallery + enquiry website with past event photos.",
            BULK_SMS:   "Seasonal SMS for wedding/festive season deal offers.",
            IVR:        "Missed-call lead capture for event enquiries.",
        },
        description = "Project-based business — portfolio visibility drives all new business.",
    ),

    # ── IT & Software ─────────────────────────────────────────
    TargetCategory(
        label    = "IT & Software Companies",
        icon     = "💻",
        tier     = "B",
        services = [SEO, WEB_DESIGN, WHATSAPP, BULK_SMS],
        search_keywords = [
            "software company", "it company", "web development company",
            "app development company", "software solutions",
            "erp company", "digital agency",
        ],
        pitch = {
            SEO:        "Rank for '[service] company in [city]' and generate inbound RFPs.",
            WEB_DESIGN: "Modern website with case studies, tech stack & client logos.",
            WHATSAPP:   "Client project updates, sprint reports & support on WhatsApp.",
            BULK_SMS:   "Product launch & webinar invite SMS to B2B contacts.",
        },
        description = "B2B tech buyers research heavily online — SEO and website are critical.",
    ),

    # ── Interior Design ───────────────────────────────────────
    TargetCategory(
        label    = "Interior Designers",
        icon     = "🛋️",
        tier     = "B",
        services = [SEO, WEB_DESIGN, WHATSAPP, BULK_SMS],
        search_keywords = [
            "interior designer", "interior design studio",
            "home interior", "office interior", "modular kitchen",
            "false ceiling contractor",
        ],
        pitch = {
            SEO:        "Rank for 'interior designer in [city]' — homebuyers search at possession.",
            WEB_DESIGN: "Portfolio website with 3D renders and before/after photos.",
            WHATSAPP:   "Share design concepts, material samples & project timelines.",
            BULK_SMS:   "Target new housing project launches with SMS campaigns.",
        },
        description = "Visual portfolio-driven business — online presence = more projects.",
    ),

    # ── Travel & Tourism ──────────────────────────────────────
    TargetCategory(
        label    = "Travel & Tourism Agencies",
        icon     = "✈️",
        tier     = "B",
        services = [BULK_SMS, WHATSAPP, SEO, WEB_DESIGN, IVR],
        search_keywords = [
            "travel agency", "tour operator", "travel company",
            "holiday packages", "visa consultant",
        ],
        pitch = {
            BULK_SMS:   "Last-minute deal SMS to customer list drives instant bookings.",
            WHATSAPP:   "Share tour itineraries, visa docs & trip updates on WhatsApp.",
            SEO:        "Rank for '[destination] tour package from [city]'.",
            WEB_DESIGN: "Package listing + online booking website.",
            IVR:        "Automated package info IVR with callback for interested leads.",
        },
        description = "Seasonal spikes + impulse buying — WhatsApp & SMS convert fast.",
    ),

    # ── Bars & Clubs ──────────────────────────────────────────
    TargetCategory(
        label    = "Bars, Clubs & Nightlife",
        icon     = "🍸",
        tier     = "B",
        services = [BULK_SMS, WHATSAPP, SEO, WEB_DESIGN],
        search_keywords = [
            "bar", "nightclub", "lounge", "pub",
            "brewery", "rooftop bar", "disc",
        ],
        pitch = {
            BULK_SMS:   "Weekend event & DJ night SMS blast drives walk-ins.",
            WHATSAPP:   "Table reservation confirmations and event invites on WhatsApp.",
            SEO:        "Rank for 'best bar in [city]' on Google & Zomato.",
            WEB_DESIGN: "Event listing + table booking website.",
        },
        description = "Weekend-driven, impulse visits — digital promotion is immediate ROI.",
    ),

    # ── Manufacturing ─────────────────────────────────────────
    TargetCategory(
        label    = "Manufacturing & Industrial",
        icon     = "🏭",
        tier     = "C",
        services = [SEO, WEB_DESIGN, BULK_SMS, WHATSAPP],
        search_keywords = [
            "manufacturer", "factory", "industrial supplier",
            "exporter", "oem manufacturer", "packaging company",
            "plastic manufacturer",
        ],
        pitch = {
            SEO:        "Rank on IndiaMART, Google & Alibaba for B2B buyer searches.",
            WEB_DESIGN: "Product catalogue website with enquiry form for bulk buyers.",
            BULK_SMS:   "Reach procurement officers via SMS for B2B outreach.",
            WHATSAPP:   "Share product specs, MOQ details & quotes on WhatsApp Business.",
        },
        description = "B2B buyers, longer sales cycles — SEO and catalogue site are essentials.",
    ),

    # ── Logistics ─────────────────────────────────────────────
    TargetCategory(
        label    = "Logistics & Supply Chain",
        icon     = "🚚",
        tier     = "C",
        services = [IVR, BULK_SMS, SEO, WEB_DESIGN, WHATSAPP],
        search_keywords = [
            "logistics company", "courier company", "transport company",
            "freight company", "warehouse", "last mile delivery",
            "cold chain logistics",
        ],
        pitch = {
            IVR:        "Automated shipment tracking IVR reduces support call volume by 70%.",
            BULK_SMS:   "Delivery update & dispatch notification SMS to customers.",
            SEO:        "Rank for 'logistics company in [city]' for B2B enquiries.",
            WEB_DESIGN: "Service area + rate calculator website for inbound leads.",
            WHATSAPP:   "Real-time delivery tracking & POD sharing on WhatsApp.",
        },
        description = "Operational communication-heavy — IVR & SMS deliver clear efficiency ROI.",
    ),

]


# ─────────────────────────────────────────────────────────────
# Lookup helpers
# ─────────────────────────────────────────────────────────────

# Index by label for fast lookup
_BY_LABEL: dict[str, TargetCategory] = {c.label: c for c in CATEGORIES}

# Index by tier
_BY_TIER: dict[str, list[TargetCategory]] = {"A": [], "B": [], "C": []}
for _cat in CATEGORIES:
    _BY_TIER[_cat.tier].append(_cat)


def get_category(label: str) -> Optional[TargetCategory]:
    """Return a TargetCategory by its label, or None."""
    return _BY_LABEL.get(label)


def get_all_labels() -> list[str]:
    """Return all category labels sorted by tier then name."""
    return [c.label for c in sorted(CATEGORIES, key=lambda x: (x.tier, x.label))]


def get_by_service(service: str) -> list[TargetCategory]:
    """Return all categories that need a specific service."""
    return [c for c in CATEGORIES if service in c.services]


def get_search_terms(label: str) -> list[str]:
    """Return the Google Places search keywords for a category."""
    cat = _BY_LABEL.get(label)
    return cat.search_keywords if cat else [label]


def get_services_needed(label: str) -> list[str]:
    """Return the ordered list of services a category needs."""
    cat = _BY_LABEL.get(label)
    return cat.services if cat else []


def get_pitch(label: str, service: str) -> str:
    """Return the one-line sales pitch for category + service combo."""
    cat = _BY_LABEL.get(label)
    if not cat:
        return ""
    return cat.pitch.get(service, "")


def get_tier_badge(tier: str) -> str:
    """Return emoji badge for a tier."""
    return {"A": "🔥 Hot", "B": "🟡 Warm", "C": "🔵 Cold"}.get(tier, tier)


# ─────────────────────────────────────────────────────────────
# Lead enrichment: tag a lead with its matched category info
# ─────────────────────────────────────────────────────────────

ALL_SERVICES = [BULK_SMS, WHATSAPP, SEO, WEB_DESIGN, IVR]

def enrich_lead_with_targeting(lead: dict) -> dict:
    """
    Add targeting metadata to a lead dict.

    Adds:
      • 'Services Needed'  — comma-separated list of services
      • 'Lead Tier'        — A / B / C
      • 'Tier Badge'       — 🔥 Hot / 🟡 Warm / 🔵 Cold
      • 'Sales Pitch'      — concatenated pitch lines
    """
    cat_label = lead.get("Category", "")
    cat       = _BY_LABEL.get(cat_label)

    if not cat:
        # Try fuzzy match on any keyword
        cat_lower = cat_label.lower()
        for c in CATEGORIES:
            if any(kw in cat_lower for kw in c.search_keywords):
                cat = c
                break

    if cat:
        lead["Services Needed"] = ", ".join(cat.services)
        lead["Lead Tier"]       = cat.tier
        lead["Tier Badge"]      = get_tier_badge(cat.tier)
        lead["Sales Pitch"]     = " | ".join(
            f"{svc}: {pitch}" for svc, pitch in cat.pitch.items()
        )
    else:
        lead["Services Needed"] = ", ".join(ALL_SERVICES)
        lead["Lead Tier"]       = "B"
        lead["Tier Badge"]      = get_tier_badge("B")
        lead["Sales Pitch"]     = ""

    return lead


def enrich_leads_with_targeting(leads: list[dict]) -> list[dict]:
    """Bulk enrich a list of lead dicts."""
    return [enrich_lead_with_targeting(lead) for lead in leads]
