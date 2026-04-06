"""Goldsboro parks scraper.

Source: https://www.goldsboroparksandrec.com/parks/

WordPress site with a listing page linking to individual park detail pages.
Detail pages have descriptions and amenity information.
"""

from __future__ import annotations

import logging
import re
import time

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_BASE_URL = "https://www.goldsboroparksandrec.com/parks/"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; NCParksBot/1.0; +https://github.com/nc-parks)"
}
REQUEST_DELAY = 0.5

_AMENITY_KEYWORDS: dict[str, str] = {
    "playground": "playground",
    "swings": "swings",
    "slide": "slides",
    "basketball": "basketball_courts",
    "tennis": "tennis_courts",
    "pickleball": "pickleball",
    "baseball": "baseball_fields",
    "softball": "baseball_fields",
    "soccer": "soccer_fields",
    "football": "sports_fields",
    "walking trail": "walking_trails",
    "trail": "walking_trails",
    "greenway": "walking_trails",
    "picnic": "picnic_shelter",
    "shelter": "picnic_shelter",
    "pavilion": "pavilion",
    "restroom": "restrooms",
    "pool": "swimming_pool",
    "splash pad": "splash_pad",
    "disc golf": "disc_golf",
    "skate": "skate_park",
    "dog park": "dog_park",
    "fishing": "fishing",
    "boat": "boat_ramp",
    "mountain bike": "mountain_biking",
}


def _extract_amenities(text: str) -> dict[str, bool]:
    amenities: dict[str, bool] = {}
    lower = text.lower()
    for keyword, key in _AMENITY_KEYWORDS.items():
        if keyword in lower:
            amenities[key] = True
    return amenities


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


def _scrape_detail(url: str) -> dict:
    """Fetch a park detail page and extract address + amenities."""
    resp = _get(url)
    soup = BeautifulSoup(resp.text, "html.parser")

    content = soup.find("div", class_="entry-content") or soup.find("article") or soup
    text = content.get_text("\n", strip=True)

    address = None
    # Look for address patterns
    addr_match = re.search(
        r"(\d+\s+[A-Z][a-zA-Z\s.]+(?:Street|St|Avenue|Ave|Boulevard|Blvd|Drive|Dr|Road|Rd|Way|Lane|Ln|Circle|Ct|Court|Hwy|Highway)[^,\n]*,?\s*Goldsboro[^,\n]*,?\s*NC\s*\d{5})",
        text,
    )
    if addr_match:
        address = addr_match.group(1).strip()
    else:
        # Try simpler pattern — just street address
        addr_match2 = re.search(
            r"(\d+\s+[A-Z][a-zA-Z\s.]+(?:Street|St|Avenue|Ave|Boulevard|Blvd|Drive|Dr|Road|Rd|Way|Lane|Ln|Circle|Ct|Court|Hwy|Highway))",
            text,
        )
        if addr_match2:
            address = f"{addr_match2.group(1).strip()}, Goldsboro, NC 27530"

    amenities = _extract_amenities(text)
    return {"address": address, "amenities": amenities}


def fetch() -> list[dict]:
    resp = _get(_BASE_URL)
    soup = BeautifulSoup(resp.text, "html.parser")

    # Collect park links from the listing page
    park_links: list[tuple[str, str]] = []
    for a in soup.find_all("a", href=re.compile(r"/parks/[a-z]")):
        href = a.get("href", "")
        name = a.get_text(strip=True)
        if not name or name.lower() in ("parks", "parks & pools"):
            continue
        if not href.startswith("http"):
            href = f"https://www.goldsboroparksandrec.com{href}"
        park_links.append((name, href))

    # Deduplicate by URL
    seen_urls: set[str] = set()
    unique_links: list[tuple[str, str]] = []
    for name, url in park_links:
        if url not in seen_urls:
            seen_urls.add(url)
            unique_links.append((name, url))

    parks: list[dict] = []
    for name, detail_url in unique_links:
        # Skip pool-only entries
        if "pool" in detail_url.lower() and "park" not in detail_url.lower():
            continue

        logger.debug("goldsboro: fetching detail — %s", detail_url)
        try:
            detail = _scrape_detail(detail_url)
        except Exception as exc:
            logger.warning("goldsboro: failed to fetch %s: %s", detail_url, exc)
            detail = {"address": None, "amenities": {}}

        source_id = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
        parks.append({
            "source": "goldsboro",
            "source_id": f"goldsboro_{source_id}",
            "name": name,
            "latitude": None,
            "longitude": None,
            "address": detail["address"],
            "city": "Goldsboro",
            "county": "Wayne County",
            "phone": None,
            "url": detail_url,
            "amenities": detail["amenities"],
            "extras": {},
        })
        time.sleep(REQUEST_DELAY)

    logger.info("goldsboro: fetched %d parks", len(parks))
    return parks


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(message)s")
    parks = fetch()
    print(f"\n{'='*60}")
    print(f"Fetched {len(parks)} Goldsboro parks")
    for p in parks:
        amenity_list = sorted(k for k, v in p.get("amenities", {}).items() if v)
        addr = p.get("address") or "N/A"
        print(f"  {p['name']:35s} | {addr:50s} | {amenity_list}")