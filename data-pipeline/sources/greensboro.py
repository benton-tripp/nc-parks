"""Greensboro neighborhood parks scraper.

Source: https://www.greensboro-nc.gov/departments/parks-recreation/parks-gardens/neighborhood-parks

The listing pages use a Granicus FacilityDirectory component paginated across
5 pages.  Each <li> entry contains:
  - Park name in a.facility_item_name
  - Coordinates in data-lat / data-long on a.facility_item_direction
  - Address in li.facility_item_address (with Google Maps link)
  - Amenities in ol.facility_item_amenties > li

The site is behind Akamai WAF which blocks requests/httpx/curl, so we use
undetected-chromedriver to fetch the pages.

Strategy:
  1. Open Chrome → fetch all 5 listing pages (/-npage-{n}/)
  2. Parse each <li> facility entry for name, coords, address, amenities
  3. Return normalized park dicts with real coordinates (no geocoding needed)
"""

from __future__ import annotations

import logging
import re
import time

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BASE_URL = "https://www.greensboro-nc.gov/departments/parks-recreation/parks-gardens/neighborhood-parks"
TOTAL_PAGES = 5
PAGE_DELAY = 3  # seconds between pages (let Akamai settle)

# Map Greensboro amenity text → normalized amenity keys
AMENITY_MAP = {
    "accessible or inclusive recreation features": "ada_accessible",
    "multipurpose court":       "basketball_courts",
    "playgrounds":              "playground",
    "playground":               "playground",
    "shelter":                  "picnic_shelter",
    "picnic shelters":          "picnic_shelter",
    "picnic shelter":           "picnic_shelter",
    "walking trail":            "walking_trails",
    "walking trails":           "walking_trails",
    "natural area":             "natural_area",
    "stream/pond":              "fishing",
    "restrooms":                "restrooms",
    "dog park":                 "dog_park",
    "disc golf":                "disc_golf",
    "tennis courts":            "tennis_courts",
    "basketball courts":        "basketball_courts",
    "ball fields":              "ball_fields",
    "swimming pool":            "swimming_pool",
    "splash pad":               "splash_pad",
    "skate park":               "skate_park",
    "greenway access":          "greenway_access",
    "gardens":                  "gardens",
    "community center":         "community_center",
    "open play area":           "open_field",
    "pavilion":                 "pavilion",
}


def _get_driver():
    """Create an undetected Chrome driver (non-headless for Akamai bypass)."""
    import undetected_chromedriver as uc
    options = uc.ChromeOptions()
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-extensions")
    driver = uc.Chrome(options=options, version_main=146)
    return driver


def _parse_facility_items(html: str) -> list[dict]:
    """Parse all <li> facility entries from page HTML."""
    soup = BeautifulSoup(html, "html.parser")
    parks = []

    # Each facility is a <li> containing a div[role="group"][aria-label="facility"]
    for item in soup.select('div[role="group"][aria-label="facility"]'):
        try:
            park = _parse_one_item(item)
            if park:
                parks.append(park)
        except Exception:
            logger.warning("Failed to parse facility item", exc_info=True)

    return parks


def _parse_one_item(item) -> dict | None:
    """Parse a single facility <div role=group> block."""
    # Name from a.facility_item_name
    name_link = item.select_one("a.facility_item_name")
    if not name_link:
        return None
    name = name_link.get_text(strip=True)
    if not name:
        return None

    href = name_link.get("href", "")
    detail_url = f"https://www.greensboro-nc.gov{href}" if href.startswith("/") else href

    # Source ID from URL: /FacilityDirectory/{id}/
    id_match = re.search(r"/FacilityDirectory/(\d+)/", href)
    source_id = id_match.group(1) if id_match else name

    # Coordinates from a.facility_item_direction data-lat / data-long
    lat = lon = None
    direction_link = item.select_one("a.facility_item_direction")
    if direction_link:
        try:
            lat = float(direction_link.get("data-lat", ""))
            lon = float(direction_link.get("data-long", ""))
        except (ValueError, TypeError):
            pass
    # Treat 0,0 as missing (Gulf of Guinea, not NC)
    if lat == 0.0 and lon == 0.0:
        lat = lon = None

    # Address from the Google Maps link inside li.facility_item_address
    address = None
    addr_link = item.select_one("li.facility_item_address a[href*='google.com/maps']")
    if addr_link:
        # The link text has street<br>city, state zip — join with ", "
        parts = []
        for child in addr_link.children:
            if hasattr(child, "name") and child.name == "br":
                continue
            text = child.get_text(strip=True) if hasattr(child, "get_text") else str(child).strip()
            if text:
                parts.append(text)
        address = ", ".join(parts) if parts else addr_link.get_text(strip=True)

    # Phone from a[href^="tel:"]
    phone = None
    phone_link = item.select_one("a[href^='tel:']")
    if phone_link:
        phone = phone_link.get_text(strip=True)

    # Amenities from ol.facility_item_amenties > li
    amenities = {}
    for li in item.select("ol.facility_item_amenties li"):
        text = li.get_text(strip=True)
        key = AMENITY_MAP.get(text.lower())
        if key:
            amenities[key] = True
        elif text:
            logger.debug("Unmapped Greensboro amenity: %r", text)

    return {
        "source": "greensboro",
        "source_id": str(source_id),
        "name": name,
        "latitude": lat,
        "longitude": lon,
        "address": address,
        "city": "Greensboro",
        "county": "Guilford",
        "phone": phone,
        "url": detail_url,
        "amenities": amenities,
    }


def fetch() -> list[dict]:
    """Fetch all Greensboro neighborhood parks using Chrome."""
    driver = _get_driver()
    all_parks = []
    seen_ids = set()

    try:
        for page_num in range(1, TOTAL_PAGES + 1):
            if page_num == 1:
                url = BASE_URL + "/"
            else:
                url = f"{BASE_URL}/-npage-{page_num}/"

            logger.info("Fetching Greensboro page %d/%d: %s", page_num, TOTAL_PAGES, url)
            driver.get(url)
            time.sleep(PAGE_DELAY)

            parks = _parse_facility_items(driver.page_source)
            new_count = 0
            for park in parks:
                if park["source_id"] not in seen_ids:
                    seen_ids.add(park["source_id"])
                    all_parks.append(park)
                    new_count += 1

            logger.info("  Page %d: %d new parks (total: %d)",
                         page_num, new_count, len(all_parks))
    finally:
        driver.quit()

    logger.info("Greensboro: fetched %d parks total", len(all_parks))
    return all_parks


# ---- CLI -----------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parks = fetch()
    print(f"\n{'='*60}")
    print(f"Fetched {len(parks)} Greensboro parks")
    has_coords = sum(1 for p in parks if p["latitude"])
    has_amenities = sum(1 for p in parks if p["amenities"])
    print(f"  With coordinates: {has_coords}")
    print(f"  With amenities:   {has_amenities}")
    for p in parks[:8]:
        amenity_list = [k for k, v in p.get("amenities", {}).items() if v]
        coord = f"({p['latitude']:.4f}, {p['longitude']:.4f})" if p["latitude"] else "no coords"
        print(f"  {p['name']:35s} | {coord:25s} | {p.get('address', 'N/A'):40s} | {amenity_list}")
    if len(parks) > 8:
        print(f"  ... and {len(parks) - 8} more")