"""Elizabeth City parks scraper.

Source: https://elizabethcitync.gov/index.asp?SEC=9A0A06B6-91C1-43C8-B01C-C0494E945138&DE=67B17754-3A18-49D3-AB59-03D5A21213B0

Catalis CMS with all parks on a single page.  Parks listed under category
headings (Playgrounds, Athletic Facilities, Greenspace/Park, Boat Ramp/Water Access)
in "Name: Address" format.
"""

from __future__ import annotations

import logging
import re

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_URL = (
    "https://elizabethcitync.gov/index.asp?"
    "SEC=9A0A06B6-91C1-43C8-B01C-C0494E945138"
    "&DE=67B17754-3A18-49D3-AB59-03D5A21213B0"
)
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; NCParksBot/1.0; +https://github.com/nc-parks)"
}

# Category → default amenity tags
_CATEGORY_AMENITIES: dict[str, dict[str, bool]] = {
    "playgrounds": {"playground": True},
    "athletic facilities": {"sports_fields": True},
    "greenspace/park": {},
    "boat ramp/water access": {"boat_ramp": True},
}


def fetch() -> list[dict]:
    resp = requests.get(_URL, headers=_HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    parks: list[dict] = []
    seen: set[str] = set()  # deduplicate (some appear in multiple categories)

    # Content is organized under bold headings followed by "Name:  Address" lines.
    # We walk through text blocks looking for category headers and entries.
    content_div = soup.find("div", {"id": "ContentArea"}) or soup.find("div", class_="widget-content") or soup
    text = content_div.get_text("\n", strip=False)

    current_category = ""
    for line in text.split("\n"):
        line = line.strip()
        if not line or line == "\xa0":
            continue

        lower = line.lower().strip()
        # Check if this line is a category header
        if lower in _CATEGORY_AMENITIES:
            current_category = lower
            continue

        # Parse "Name: Address" or "Name:  Address"
        match = re.match(r"^(.+?):\s{1,4}(.+)$", line)
        if match:
            name = match.group(1).strip()
            address_raw = match.group(2).strip()
            # Skip non-park entries
            if not name or name.lower() in ("phone", "mailing address", "location"):
                continue

            # Build full address
            if "elizabeth city" not in address_raw.lower():
                address = f"{address_raw}, Elizabeth City, NC 27909"
            else:
                address = address_raw

            # Deduplicate by name
            name_key = name.lower()
            category_amenities = dict(_CATEGORY_AMENITIES.get(current_category, {}))
            if name_key in seen:
                # Merge amenities into existing entry
                for p in parks:
                    if p["name"].lower() == name_key:
                        p["amenities"].update(category_amenities)
                        break
                continue

            seen.add(name_key)
            source_id = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
            parks.append({
                "source": "elizabeth_city",
                "source_id": f"elizabeth_city_{source_id}",
                "name": name,
                "latitude": None,
                "longitude": None,
                "address": address,
                "city": "Elizabeth City",
                "county": "Pasquotank County",
                "phone": None,
                "url": _URL,
                "amenities": category_amenities,
                "extras": {"category": current_category},
            })

    logger.info("elizabeth_city: fetched %d parks", len(parks))
    return parks


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(message)s")
    parks = fetch()
    print(f"\n{'='*60}")
    print(f"Fetched {len(parks)} Elizabeth City parks")
    for p in parks:
        amenity_list = sorted(k for k, v in p.get("amenities", {}).items() if v)
        addr = p.get("address") or "N/A"
        print(f"  {p['name']:45s} | {addr:55s} | {amenity_list}")