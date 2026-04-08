"""Playground Explorers scraper.

Source: https://www.playgroundexplorers.com/playgrounds/north-carolina

A Next.js site that embeds all 141 NC playground listings (with coordinates) in
RSC flight data on the state listing page.  Detail pages add rich amenity and
accessibility info.

Strategy:
  1. GET the NC state listing page — parse RSC flight data for all playgrounds
     (id, title, slug, type, location with GeoJSON coordinates)
  2. For each *outdoor* playground, GET the detail page — parse RSC flight data
     for amenities (slides, swings, ADA, restrooms, etc.), hours, phone, website
  3. Skip indoor/commercial venues (trampoline parks, indoor play centers)
"""

from __future__ import annotations

import json
import logging
import re
import time

import requests

logger = logging.getLogger(__name__)

LISTING_URL = "https://www.playgroundexplorers.com/playgrounds/north-carolina"
DETAIL_BASE = "https://www.playgroundexplorers.com/playgrounds"
REQUEST_DELAY = 0.5  # seconds between detail page fetches

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
    ),
}

# Map Playground Explorers boolean fields → our canonical amenity keys
AMENITY_MAP = {
    "slides_available":              "slides",
    "swings_available":              "swings",
    "climbing_structures_available": "playground",
    "sandbox_available":             "sandbox",
    "seesaws_available":             "playground",
    "zip_line_available":            "playground",
    "water_features":                "splash_pad",
    "ada_accessible":                "ada_accessible",
    "toddler_area_available":        "fenced_playground",
    "shaded_areas_available":        "shaded_areas",
    "picnic_tables_available":       "picnic_tables",
    "benches_available":             "picnic_tables",
    "drinking_fountain_available":   "drinking_water",
    "parking_available":             "parking",
    "restrooms_available":           "restrooms",
    "family_restroom_available":     "restrooms",
}


# ---- RSC flight data extraction ------------------------------------------

def _extract_rsc_chunks(html: str) -> list[str]:
    """Extract and unescape all RSC flight data chunks from a Next.js page."""
    chunks = []
    for m in re.finditer(
        r'self\.__next_f\.push\(\[1,"(.+?)"\]\)', html, re.DOTALL
    ):
        raw = m.group(1)
        unescaped = raw.replace('\\"', '"').replace('\\n', '\n').replace('\\\\', '\\')
        chunks.append(unescaped)
    return chunks


def _extract_json_object(text: str, start_idx: int) -> dict | None:
    """Extract a balanced JSON object starting at ``start_idx`` in *text*."""
    depth = 0
    for j in range(start_idx, len(text)):
        if text[j] == '{':
            depth += 1
        elif text[j] == '}':
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start_idx:j + 1])
                except json.JSONDecodeError:
                    return None
    return None


# ---- Listing page --------------------------------------------------------

def _fetch_listing() -> list[dict]:
    """Fetch the NC state listing and return all playground stubs."""
    resp = requests.get(LISTING_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()

    for chunk in _extract_rsc_chunks(resp.text):
        idx = chunk.find('"initialData":')
        if idx < 0:
            continue
        obj_start = idx + len('"initialData":')
        data = _extract_json_object(chunk, obj_start)
        if data and "playgrounds" in data:
            playgrounds = data["playgrounds"]
            logger.info("Listing page: %d playgrounds found", len(playgrounds))
            return playgrounds

    logger.warning("Could not extract initialData from listing page")
    return []


# ---- Detail page ---------------------------------------------------------

def _fetch_detail(slug: str) -> dict | None:
    """Fetch a detail page and return the full playground object."""
    url = f"{DETAIL_BASE}/{slug}"
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()

    for chunk in _extract_rsc_chunks(resp.text):
        if "restrooms_available" not in chunk:
            continue
        # Find "playground": { ... }
        pg_idx = chunk.find('"playground":')
        if pg_idx < 0:
            continue
        obj_start = pg_idx + len('"playground":')
        obj = _extract_json_object(chunk, obj_start)
        if obj and "location" in obj:
            return obj

    logger.warning("Could not extract playground data from %s", url)
    return None


def _parse_amenities(detail: dict) -> dict[str, bool]:
    """Convert detail page boolean fields to canonical amenity dict."""
    amenities: dict[str, bool] = {}
    for field, canonical in AMENITY_MAP.items():
        if detail.get(field):
            amenities[canonical] = True
    return amenities


def _to_park(stub: dict, detail: dict | None) -> dict:
    """Merge listing stub + optional detail into our park schema."""
    loc = stub.get("location", {})
    coords = loc.get("coordinates", {}).get("coordinates", [])
    lon = coords[0] if len(coords) > 0 else None
    lat = coords[1] if len(coords) > 1 else None

    address_parts = []
    if loc.get("street"):
        address_parts.append(loc["street"])
    city = loc.get("city")
    state_abbr = "NC"
    zipcode = loc.get("zip")
    if city:
        address_parts.append(f"{city}, {state_abbr}")
    if zipcode:
        # Append zip to last part
        if address_parts:
            address_parts[-1] += f" {zipcode}"
        else:
            address_parts.append(zipcode)
    address = ", ".join(address_parts) if address_parts else None

    amenities = {}
    phone = None
    website = None
    hours = None
    accessibility = None
    free = None

    if detail:
        amenities = _parse_amenities(detail)
        biz = detail.get("businessInfo", {})
        phone = biz.get("phone") or None
        website = biz.get("website") or None
        hours = biz.get("business_hours") or None
        accessibility = detail.get("accessibility_features") or None
        admission = detail.get("admissionInfo", {})
        free = admission.get("free_admission")

    # Use the detail URL as the park URL (links to Playground Explorers page)
    detail_url = f"{DETAIL_BASE}/{stub['slug']}"

    return {
        "source": "playground_explorers",
        "source_id": stub.get("id", ""),
        "name": stub.get("title", ""),
        "latitude": lat,
        "longitude": lon,
        "address": address,
        "city": city,
        "county": None,  # enricher fills this
        "phone": phone,
        "url": website or detail_url,
        "amenities": amenities,
        "extras": {
            "pe_url": detail_url,
            "pe_type": stub.get("type"),
            "accessibility": accessibility,
            "hours": hours,
            "free_admission": free,
        },
    }


# ---- Public API ----------------------------------------------------------

def fetch() -> list[dict]:
    """Fetch all outdoor NC playgrounds from Playground Explorers."""
    stubs = _fetch_listing()
    if not stubs:
        return []

    # Filter to outdoor only — skip indoor/commercial venues
    outdoor = [s for s in stubs if s.get("type") == "outdoor"]
    indoor_count = len(stubs) - len(outdoor)
    if indoor_count:
        logger.info("Skipping %d indoor venues, keeping %d outdoor",
                     indoor_count, len(outdoor))

    parks = []
    for i, stub in enumerate(outdoor):
        slug = stub.get("slug", "")
        logger.info("Fetching detail %d/%d: %s", i + 1, len(outdoor), slug)

        detail = None
        try:
            detail = _fetch_detail(slug)
        except Exception:
            logger.warning("Failed to fetch detail for %s", slug, exc_info=True)

        park = _to_park(stub, detail)
        parks.append(park)

        if i < len(outdoor) - 1:
            time.sleep(REQUEST_DELAY)

    logger.info("Playground Explorers: %d outdoor parks fetched "
                "(%d with detail)", len(parks),
                sum(1 for p in parks if p.get("amenities")))
    return parks


# ---- CLI -----------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(message)s")
    parks = fetch()
    print(f"\n{'='*60}")
    print(f"Fetched {len(parks)} parks from Playground Explorers")
    for p in parks:
        amenity_list = [k for k, v in p.get("amenities", {}).items() if v]
        print(f"  {p['name']:45s} | {p.get('city', '?'):20s} | {amenity_list}")
