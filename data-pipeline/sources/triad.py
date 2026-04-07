"""NC Triad Outdoors playground scraper.

Source: https://nctriadoutdoors.com/playgrounds/

WordPress site using GeoDirectory plugin.  The listing page links to
individual place pages.  Each detail page embeds JSON-LD structured data
(LocalBusiness schema) with name, address, coordinates, and categories.
Plain ``requests`` is sufficient — no WAF.
"""

from __future__ import annotations

import json
import logging
import re
import time

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_LISTING_URL = "https://nctriadoutdoors.com/playgrounds/"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}
REQUEST_DELAY = 0.5  # polite delay between detail page fetches

# Map GeoDirectory categories → normalised amenity keys
_CATEGORY_MAP: dict[str, str] = {
    "playground": "playground",
    "picnic area": "picnic_shelter",
    "sports facilities": "sports_fields",
    "baseball/softball": "baseball_fields",
    "disc golf": "disc_golf",
    "greenway": "walking_trails",
    "soccer": "soccer_fields",
    "dog park": "dog_park",
    "tennis": "tennis_courts",
    "basketball": "basketball_courts",
    "swimming": "swimming_pool",
    "fishing": "fishing",
    "kayak/canoe": "kayak_access",
    "mountain biking": "mountain_biking",
    "pickleball": "pickleball",
    "skate park": "skate_park",
}


def _get(url: str, retries: int = 3) -> requests.Response:
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=_HEADERS, timeout=20)
            resp.raise_for_status()
            return resp
        except requests.RequestException:
            if attempt == retries - 1:
                raise
            time.sleep(REQUEST_DELAY * (attempt + 1))
    raise RuntimeError("unreachable")


def _get_place_urls(soup: BeautifulSoup) -> list[str]:
    """Extract unique /places/ URLs from the listing page."""
    seen: set[str] = set()
    urls: list[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/places/" in href and href not in seen:
            seen.add(href)
            urls.append(href)
    return urls


def _parse_detail(url: str) -> dict | None:
    """Fetch a detail page, extract JSON-LD + categories."""
    resp = _get(url)
    soup = BeautifulSoup(resp.text, "html.parser")

    # --- JSON-LD structured data ---
    ld_data: dict | None = None
    for script in soup.find_all("script", type="application/ld+json"):
        if not script.string:
            continue
        try:
            data = json.loads(script.string)
        except json.JSONDecodeError:
            continue
        schema_type = data.get("@type", "")
        if schema_type in ("LocalBusiness", "Park", "Place", "TouristAttraction"):
            ld_data = data
            break

    if not ld_data or not ld_data.get("name"):
        logger.debug("triad: no JSON-LD for %s", url)
        return None

    name = ld_data["name"]

    # Address
    addr_obj = ld_data.get("address", {})
    street = addr_obj.get("streetAddress", "")
    city = addr_obj.get("addressLocality", "")
    state = addr_obj.get("addressRegion", "")
    zipcode = addr_obj.get("postalCode", "")
    address_parts = [p for p in (street, city, state, zipcode) if p]
    address = ", ".join(address_parts) if address_parts else None

    # Coordinates
    geo = ld_data.get("geo", {})
    lat = _safe_float(geo.get("latitude"))
    lng = _safe_float(geo.get("longitude"))

    # Description
    description = ld_data.get("description", "")

    # Categories → amenities
    categories = [
        a.get_text(strip=True)
        for a in soup.select('a[href*="/category/"]')
    ]
    amenities: dict[str, bool] = {}
    for cat in categories:
        key = _CATEGORY_MAP.get(cat.lower())
        if key:
            amenities[key] = True

    source_id = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")

    return {
        "source": "triad",
        "source_id": f"triad_{source_id}",
        "name": name,
        "latitude": lat,
        "longitude": lng,
        "address": address,
        "city": city or None,
        "county": None,  # geocoder / enrich will fill
        "phone": None,
        "url": url,
        "amenities": amenities,
        "extras": {"description": description} if description else {},
    }


def _safe_float(val) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def fetch() -> list[dict]:
    logger.info("triad: fetching listing %s", _LISTING_URL)
    resp = _get(_LISTING_URL)
    soup = BeautifulSoup(resp.text, "html.parser")

    place_urls = _get_place_urls(soup)
    logger.info("triad: found %d place links", len(place_urls))

    parks: list[dict] = []
    for url in place_urls:
        time.sleep(REQUEST_DELAY)
        try:
            park = _parse_detail(url)
            if park:
                parks.append(park)
        except Exception as exc:
            logger.warning("triad: failed to parse %s: %s", url, exc)

    logger.info("triad: fetched %d parks", len(parks))
    return parks


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(message)s")
    parks = fetch()
    print(f"\n{'=' * 60}")
    print(f"Fetched {len(parks)} Triad parks")
    for p in parks:
        addr = p.get("address") or "N/A"
        cats = sorted(p.get("amenities", {}).keys())
        print(f"  {p['name']:40s} | {addr}")
        if cats:
            print(f"  {'':40s} | amenities: {cats}")