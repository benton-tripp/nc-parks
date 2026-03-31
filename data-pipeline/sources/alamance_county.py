"""Alamance County parks scraper.

Source: https://parks.alamancecountync.gov/

Strategy:
  1. Hard-coded park list with addresses from the county site footer
     (only 6 parks — stable enough to maintain manually)
  2. Cedarock Park: sidebar nav sub-page links = amenities
     (Trails, Camping, Disc Golf, Kayak, Picnicking, Fishing, etc.)
  3. Other 5 parks: fetch their "Activities" page and extract headings
     that map to normalized amenity keys
  4. No coordinates on the site — the pipeline's geocoder handles that
"""

from __future__ import annotations

import logging
import re
import time

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BASE_URL = "https://parks.alamancecountync.gov"

# Delay between requests to be polite
REQUEST_DELAY = 0.5

# ── Park definitions ─────────────────────────────────────────────────────
# Addresses come from the site footer "Parks and Trails" section.
# About-page URLs are the main page for each park.
# Activity URLs point to the page listing activities/amenities.

PARKS = [
    {
        "name": "Cedarock Park",
        "address": "4242 R. Dean Coleman Rd., Burlington, NC 27215",
        "latitude": 36.0032,
        "longitude": -79.4681,
        "about_url": f"{BASE_URL}/outdoors-2/about-cedarock-park/",
        "activity_url": None,  # amenities come from sidebar nav links
        "hours_url": f"{BASE_URL}/outdoors-2/about-cedarock-park/crp-location-hours-rules/",
    },
    {
        "name": "Great Bend Park",
        "address": "350 Greenwood Drive, Burlington, NC 27217",
        "latitude": 36.0400,
        "longitude": -79.4825,
        "about_url": f"{BASE_URL}/outdoors-2/hrt/great-bend-park/",
        "activity_url": f"{BASE_URL}/outdoors-2/hrt/great-bend-park/activities/",
        "hours_url": f"{BASE_URL}/outdoors-2/hrt/great-bend-park/gb-location-hours-rules/",
    },
    {
        "name": "Shallowford Natural Area",
        "address": "1955 Gerringer Mill Road, Elon, NC 27244",
        "latitude": 36.1160,
        "longitude": -79.5270,
        "about_url": f"{BASE_URL}/outdoors-2/hrt/shallow-ford-natural-area/",
        "activity_url": f"{BASE_URL}/outdoors-2/hrt/shallow-ford-natural-area/sfna-activities/",
        "hours_url": f"{BASE_URL}/outdoors-2/hrt/shallow-ford-natural-area/sfna-location-hours-rules/",
    },
    {
        "name": "Saxapahaw Island Park",
        "address": "5550 Church Road, Graham, NC 27253",
        "latitude": 35.9475,
        "longitude": -79.3213,
        "about_url": f"{BASE_URL}/outdoors-2/hrt/about-saxapahaw/",
        "activity_url": f"{BASE_URL}/outdoors-2/hrt/about-saxapahaw/sax_island_park_activities/",
        "hours_url": f"{BASE_URL}/outdoors-2/hrt/about-saxapahaw/sfna-location-hours-rules-2/",
    },
    {
        "name": "Swepsonville River Park",
        "address": "2472 Boywood Road, Swepsonville, NC 27359",
        "latitude": 35.9670,
        "longitude": -79.3570,
        "about_url": f"{BASE_URL}/swepsonville-river-park/",
        "activity_url": f"{BASE_URL}/swepsonville-river-park-activities/",
        "hours_url": f"{BASE_URL}/swepsonville-river-park-hours-rules/",
    },
    {
        "name": "Cane Creek Mountains Natural Area",
        "address": "5075 Bass Mountain Rd, Snow Camp, NC 27349",
        "latitude": 35.8846,
        "longitude": -79.3950,
        "about_url": f"{BASE_URL}/outdoors-2/cane-creek-mountains-natural-area/",
        "activity_url": f"{BASE_URL}/outdoors-2/cane-creek-mountains-natural-area/cane-creek-mountains-natural-area-activities/",
        "hours_url": f"{BASE_URL}/outdoors-2/cane-creek-mountains-natural-area/location-hours-rules/",
    },
]

# ── Amenity mapping ──────────────────────────────────────────────────────
# Sidebar nav link text (Cedarock) and activity page headings → normalized keys.

AMENITY_MAP = {
    # Cedarock sidebar nav links
    "trails":               "walking_trails",
    "camping":              "camping",
    "kayak & canoe rentals": "canoe_kayak",
    "disc golf":            "disc_golf",
    "footgolf":             "footgolf",
    "open play":            "open_play",
    "picnicking":           "picnic_shelter",
    "fishing":              "fishing",
    "cedarock equestrian center": "equestrian",
    "cedarock historical farm":   "historical_site",
    # Activity page headings (other parks)
    "hiking overview & map": "walking_trails",
    "hiking":               "walking_trails",
    "paddle the haw":       "canoe_kayak",
    "paddling":             "canoe_kayak",
    "observing nature":     "nature_observation",
    "camping at shallow ford": "camping",
    "kids in parks track trail": "walking_trails",
    "picnics & gatherings": "picnic_shelter",
    "playground":           "playground",
    "riverfront view":      "scenic_view",
    "stroll through history": "walking_trails",
    "fishing":              "fishing",
}

# Headings from activity pages to ignore (footer park names, admin, etc.)
_IGNORE_HEADINGS = {
    "cedarock park", "great bend park", "shallowford natural area",
    "saxapahaw island park", "swepsonville river park",
    "cane creek mountains natural area",
    "parks and recreation administrative location",
    "cedarock shop & visitors center", "phone:", "parks and trails",
    "learn to identify trees",
}

# ── Helpers ───────────────────────────────────────────────────────────────

def _get(url: str) -> requests.Response:
    """GET with retries and a browser-like User-Agent."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        )
    }
    for attempt in range(3):
        try:
            resp = requests.get(url, headers=headers, timeout=20)
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            if attempt == 2:
                raise
            logger.warning("Retry %d for %s: %s", attempt + 1, url, exc)
            time.sleep(2)


def _normalize_amenity(text: str) -> str | None:
    """Map a heading or nav link text to a normalized amenity key."""
    lower = text.strip().lower()
    if lower in AMENITY_MAP:
        return AMENITY_MAP[lower]
    # Substring match
    for keyword, key in AMENITY_MAP.items():
        if keyword in lower:
            return key
    return None


def _scrape_cedarock_amenities(about_url: str) -> dict[str, bool]:
    """Extract amenities from Cedarock Park's sidebar navigation links.

    The sidebar has direct links to activity sub-pages (Trails, Camping,
    Disc Golf, etc.) — each link text maps to an amenity.
    """
    resp = _get(about_url)
    soup = BeautifulSoup(resp.text, "html.parser")
    amenities = {}

    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)
        # Only look at sub-pages of Cedarock
        if not text or not href.startswith(about_url) or href == about_url:
            continue
        # Skip location/hours/rules pages
        if any(skip in href.lower() for skip in ("location", "hours", "rules")):
            continue
        key = _normalize_amenity(text)
        if key:
            amenities[key] = True
            logger.debug("  Cedarock amenity: %s -> %s", text, key)
        else:
            logger.debug("  Cedarock unmapped nav link: %s", text)

    return amenities


def _scrape_activity_page(activity_url: str) -> dict[str, bool]:
    """Extract amenities from an activities page by scanning headings.

    The activities pages use h2/h3/h4/strong headings for each activity
    (e.g., "Hiking Overview & Map", "Playground", "Fishing").
    """
    resp = _get(activity_url)
    soup = BeautifulSoup(resp.text, "html.parser")
    amenities = {}

    for heading in soup.find_all(["h2", "h3", "h4", "strong"]):
        text = heading.get_text(strip=True)
        if not text or len(text) > 60:
            continue
        if text.strip().lower() in _IGNORE_HEADINGS:
            continue
        key = _normalize_amenity(text)
        if key:
            amenities[key] = True
            logger.debug("  Activity heading: %s -> %s", text, key)

    return amenities


def _scrape_hours(hours_url: str) -> str | None:
    """Try to extract hours from a location/hours page.

    Looks for a heading containing 'Hours' and extracts the text after it,
    ignoring sidebar navigation and footer content.
    """
    try:
        resp = _get(hours_url)
        soup = BeautifulSoup(resp.text, "html.parser")

        # Strategy: find a heading with "Hours" in the main content,
        # then grab the text that follows it.
        for heading in soup.find_all(["h2", "h3", "h4", "strong"]):
            text = heading.get_text(strip=True)
            if not re.search(r'\bhours\b', text, re.IGNORECASE):
                continue
            # Skip sidebar/nav headings (they contain commas like "Location, Hours, & Rules")
            if "," in text:
                continue

            # Get the next sibling(s) text
            parts = []
            for sib in heading.find_next_siblings():
                sib_text = sib.get_text(" ", strip=True)
                if not sib_text:
                    continue
                # Stop at the next heading
                if sib.name in ("h2", "h3", "h4"):
                    break
                parts.append(sib_text)
                if len(parts) >= 3:
                    break

            if parts:
                hours_text = " ".join(parts)
                # Clean up and truncate to something reasonable
                hours_text = re.sub(r'\s+', ' ', hours_text).strip()
                if len(hours_text) > 120:
                    hours_text = hours_text[:120].rsplit(" ", 1)[0] + "..."
                return hours_text

        # Fallback: look for "dawn to dusk" or "8am-8pm" style patterns
        main = soup.find("main") or soup.find("article") or soup
        main_text = main.get_text(" ", strip=True)
        fallback_patterns = [
            r'(dawn\s+to\s+dusk)',
            r'(open\s+\d{1,2}\s*(?:am|AM)\s*[-–]\s*[A-Za-z0-9 ]{3,30})',
        ]
        for pattern in fallback_patterns:
            match = re.search(pattern, main_text, re.IGNORECASE)
            if match:
                return match.group(1).strip()

    except Exception as exc:
        logger.debug("Could not fetch hours from %s: %s", hours_url, exc)
    return None


# ── Main fetch ────────────────────────────────────────────────────────────

def fetch() -> list[dict]:
    """Fetch all Alamance County parks.

    Returns a list of park dicts in the pipeline's raw schema.
    """
    results = []

    for park_def in PARKS:
        name = park_def["name"]
        logger.info("Scraping %s ...", name)

        # --- Amenities ---
        amenities = {}
        try:
            if name == "Cedarock Park":
                amenities = _scrape_cedarock_amenities(park_def["about_url"])
            elif park_def["activity_url"]:
                amenities = _scrape_activity_page(park_def["activity_url"])
                time.sleep(REQUEST_DELAY)
        except Exception as exc:
            logger.warning("Failed to scrape amenities for %s: %s", name, exc)

        # --- Hours ---
        hours = None
        try:
            hours = _scrape_hours(park_def["hours_url"])
            time.sleep(REQUEST_DELAY)
        except Exception as exc:
            logger.debug("Failed to scrape hours for %s: %s", name, exc)

        park = {
            "source": "alamance_county",
            "source_id": f"alamance_{name.lower().replace(' ', '_').replace(',', '')}",
            "name": name,
            "latitude": park_def.get("latitude"),
            "longitude": park_def.get("longitude"),
            "county": "Alamance",
            "state": "NC",
            "address": park_def["address"],
            "amenities": amenities,
            "url": park_def["about_url"],
            "phone": "(336) 229-2410",
            "description": None,
            "hours": hours,
        }
        results.append(park)
        logger.info("  %s: %d amenities", name, len(amenities))

    logger.info("Alamance County: %d parks fetched", len(results))
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")
    parks = fetch()
    print(f"\nTotal: {len(parks)} parks")
    for p in parks:
        amenity_count = sum(1 for v in p["amenities"].values() if v)
        print(f"  {p['name']}")
        print(f"    Address: {p['address']}")
        print(f"    Amenities ({amenity_count}): {', '.join(sorted(p['amenities']))}")
        if p["hours"]:
            print(f"    Hours: {p['hours']}")
        print()