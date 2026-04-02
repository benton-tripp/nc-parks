"""High Point parks scraper.

Source: https://www.highpointnc.gov/Facilities

CivicPlus Facility Directory with paginated listing and detail pages.
The listing uses JavaScript pagination (SearchSidebar.searchByPage), so we use
undetected-chromedriver to change pageSize to 100 and grab all facility URLs at
once.  Detail pages are fetched with plain requests (no WAF issues).

Each detail page has: name, address, phone, features list, acreage, and photos.
No coordinates in HTML — the pipeline geocoder fills those from the address.

Strategy:
  1. Selenium: load /Facilities, set pageSize=100, trigger search → all URLs
  2. requests: fetch each detail page → extract features, address, size, phone
  3. No coordinates in HTML → rely on pipeline geocoder
"""

from __future__ import annotations

import logging
import re
import time

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

LISTING_URL = "https://www.highpointnc.gov/Facilities"
REQUEST_DELAY = 0.5  # seconds between detail page fetches

# Map CivicPlus feature text → normalized amenity keys
FEATURE_MAP = {
    "ada accessible":               "ada_accessible",
    "basketball court(s)":          "basketball_courts",
    "basketball courts":            "basketball_courts",
    "batting cages":                "ball_fields",
    "disc golf":                    "disc_golf",
    "dog park":                     "dog_park",
    "fishing":                      "fishing",
    "greenway access":              "greenway_access",
    "lighted athletic field(s)":    "ball_fields",
    "lighted tennis courts":        "tennis_courts",
    "maintenance complex":          "community_center",
    "multipurpose athletic field(s)": "multipurpose_field",
    "multipurpose room(s)":         "community_center",
    "nature trail(s)":              "walking_trails",
    "outdoor pool":                 "swimming_pool",
    "pickleball courts":            "pickleball",
    "picnic shelters":              "picnic_shelter",
    "picnic shelter(s)":            "picnic_shelter",
    "playground":                   "playground",
    "restrooms":                    "restrooms",
    "sand volleyball":              "sand_volleyball",
    "skate park":                   "skate_park",
    "splash pad":                   "splash_pad",
    "tennis court(s)":              "tennis_courts",
    "tennis courts":                "tennis_courts",
    "walking trail(s)":             "walking_trails",
    "walking trails":               "walking_trails",
    "youth baseball field":         "ball_fields",
    "youth baseball field(s)":      "ball_fields",
    "youth softball field(s)":      "ball_fields",
    "amphitheater":                 "theater",
    "boat launch/pier":             "boat_rental",
    "canoe/kayak launch":           "canoe_kayak",
    "concessions":                  "concessions",
    "gymnasium":                    "gym",
    "horseshoe pits":               "horseshoe",
    "lake access":                  "fishing",
    "senior center":                "community_center",
    "sheltered picnic tables":      "picnic_shelter",
    "open play area":               "open_field",
    "fitness trail":                "walking_trails",
    "gardens":                      "gardens",
    "gazebo":                       "pavilion",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; NCParksBot/1.0; +https://github.com/nc-parks)"
}

# Facility names/keywords that indicate non-park entries to skip
_SKIP_KEYWORDS = {
    "library", "conference room", "city hall", "municipal building",
    "museum", "blacksmith", "theater", "theatre", "classroom",
    "education", "collection center", "landfill", "compost",
    "lecture gallery", "meeting house", "store", "hoggatt house",
    "haley house", "administration office", "administration",
}


def _get_driver():
    """Create an undetected Chrome driver (non-headless for JS execution)."""
    import undetected_chromedriver as uc
    options = uc.ChromeOptions()
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-extensions")
    driver = uc.Chrome(options=options, version_main=146)
    return driver


def _get_listing_urls() -> list[str]:
    """Use Selenium to load all facility URLs from the paginated listing."""
    driver = _get_driver()
    try:
        driver.get(LISTING_URL)
        time.sleep(3)

        # Change page size to 100 to show all facilities on one page
        driver.execute_script("""
            var sel = document.getElementById('facilityListingPagingDropDown');
            if (sel) { sel.value = '100'; sel.dispatchEvent(new Event('change')); }
        """)
        time.sleep(2)

        # Trigger search to reload with new page size
        driver.execute_script("SearchSidebar.searchByPage(1);")
        time.sleep(5)

        html = driver.page_source
    finally:
        try:
            driver.quit()
        except OSError:
            pass

    soup = BeautifulSoup(html, "html.parser")
    seen = set()
    urls = []

    for link in soup.select('a[href*="/Facilities/Facility/Details/"]'):
        href = link.get("href", "")
        full = f"https://www.highpointnc.gov{href}" if href.startswith("/") else href
        full = full.split("?")[0]
        if full not in seen:
            seen.add(full)
            # Extract name to check skip list
            name = link.get_text(strip=True)
            name_lower = name.lower() if name else ""
            if any(kw in name_lower for kw in _SKIP_KEYWORDS):
                if "park" not in name_lower:
                    logger.debug("Skipping non-park facility from listing: %s", name)
                    continue
            urls.append(full)

    logger.info("Selenium: found %d facility URLs (after filtering)", len(urls))
    return urls


def _parse_detail_page(html: str, url: str) -> dict | None:
    """Parse a single facility detail page."""
    soup = BeautifulSoup(html, "html.parser")

    # Name — in h2 or h4 tag
    name = None
    for tag in ["h2", "h4"]:
        heading = soup.find(tag)
        if heading:
            text = heading.get_text(strip=True)
            if text and "Facilities" not in text and "Rating" not in text:
                name = text
                break

    if not name:
        return None

    # Extract ID from URL
    id_match = re.search(r"-(\d+)$", url.rstrip("/"))
    source_id = id_match.group(1) if id_match else name

    # Check if this is actually a park (skip non-park facilities)
    name_lower = name.lower()
    if any(kw in name_lower for kw in _SKIP_KEYWORDS):
        # But keep it if name also contains "park"
        if "park" not in name_lower:
            logger.debug("Skipping non-park facility: %s", name)
            return None

    # Address — look for the address block near the name heading
    address = None
    # CivicPlus puts address in a div after the h4 heading
    body_text = soup.get_text("\n", strip=True)

    # Address pattern: street + city, state zip after the facility name
    addr_match = re.search(
        r"(\d+\s+[A-Za-z0-9 .]+(?:St|Ave|Rd|Dr|Blvd|Way|Ln|Ct|Pl|Pkwy|Circle|Loop|Trail|Park)[.\s]*)"
        r"[,\s]*(High Point),?\s*NC\s*(\d{5})",
        body_text
    )
    if addr_match:
        street = addr_match.group(1).strip().rstrip(".")
        city = addr_match.group(2)
        zipcode = addr_match.group(3)
        address = f"{street}, {city}, NC {zipcode}"

    # Phone
    phone = None
    phone_link = soup.find("a", href=re.compile(r"^tel:"))
    if phone_link:
        phone = phone_link.get_text(strip=True)

    # Features — in the "Features" section, typically as bullet list
    amenities = {}
    features_heading = soup.find(string=re.compile(r"^\s*Features\s*$"))
    if features_heading:
        # Get the parent element and look for the next list
        parent = features_heading.find_parent()
        if parent:
            # Look for bullet list items after this heading
            ul = parent.find_next("ul")
            if ul:
                for li in ul.find_all("li"):
                    text = li.get_text(strip=True)
                    if text:
                        key = FEATURE_MAP.get(text.lower())
                        if key:
                            amenities[key] = True
                        else:
                            logger.debug("Unmapped HP feature: %r", text)

    # If no UL found, try parsing bullet text from the Features section
    if not amenities and features_heading:
        parent = features_heading.find_parent()
        if parent:
            sibling = parent.find_next_sibling()
            if sibling:
                for line in sibling.get_text("\n").split("\n"):
                    line = line.strip().lstrip("•·▪-").strip()
                    if line:
                        key = FEATURE_MAP.get(line.lower())
                        if key:
                            amenities[key] = True

    # Size (acres) — in the "Size" section
    size_acres = None
    size_match = re.search(r"This park is ([\d.]+) acres", body_text)
    if size_match:
        size_acres = float(size_match.group(1))

    return {
        "source": "high_point",
        "source_id": str(source_id),
        "name": name,
        "latitude": None,   # geocoder fills this from address
        "longitude": None,
        "address": address,
        "city": "High Point",
        "county": "Guilford",
        "phone": phone,
        "url": url,
        "amenities": amenities,
        "extras": {
            "size_acres": size_acres,
        },
    }


def fetch() -> list[dict]:
    """Fetch all High Point parks — Selenium listing + requests detail pages."""
    # Step 1: Get all detail page URLs via Selenium
    detail_urls = _get_listing_urls()
    logger.info("Found %d facility detail URLs", len(detail_urls))

    # Step 2: Fetch each detail page with plain requests
    session = requests.Session()
    session.headers.update(HEADERS)

    parks = []
    for i, url in enumerate(detail_urls):
        logger.info("Fetching detail %d/%d: %s", i + 1, len(detail_urls), url)
        try:
            resp = session.get(url, timeout=30)
            resp.raise_for_status()
            park = _parse_detail_page(resp.text, url)
            if park:
                parks.append(park)
        except Exception:
            logger.warning("Failed to fetch %s", url, exc_info=True)

        if i < len(detail_urls) - 1:
            time.sleep(REQUEST_DELAY)

    logger.info("High Point: fetched %d parks from %d facility pages",
                len(parks), len(detail_urls))
    return parks


# ---- CLI -----------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(message)s")
    parks = fetch()
    print(f"\n{'='*60}")
    print(f"Fetched {len(parks)} High Point parks")
    for p in parks:
        amenity_list = [k for k, v in p.get("amenities", {}).items() if v]
        acres = p.get("extras", {}).get("size_acres") or "?"
        addr = p.get("address") or "N/A"
        print(f"  {p['name']:35s} | {addr:45s} | {acres} ac | {amenity_list}")