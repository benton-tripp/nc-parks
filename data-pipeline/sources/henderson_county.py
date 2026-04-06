"""Henderson County parks scraper.

Source: https://www.hendersoncountync.gov/recreation/page/parks-facilities

Drupal site with parks listed in an HTML table (Name, Address with city/state).
Also has sidebar links to individual park detail pages.
"""

from __future__ import annotations

import logging
import re

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_URL = "https://www.hendersoncountync.gov/recreation/page/parks-facilities"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; NCParksBot/1.0; +https://github.com/nc-parks)"
}


def fetch() -> list[dict]:
    resp = requests.get(_URL, headers=_HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    parks: list[dict] = []
    seen: set[str] = set()

    # Parse table rows — each row has cells like:
    # | Name | "Name Address City, NC ZIP See map: Google Maps" |
    for row in soup.select("table tr"):
        cells = row.find_all("td")
        if len(cells) < 2:
            continue

        name = cells[0].get_text(strip=True)
        if not name:
            continue

        # The 2nd cell contains: "ParkName FullAddress See map: Google Maps"
        cell_text = cells[1].get_text("\n", strip=True)
        # Extract address — look for pattern: number + street + city, NC ZIP
        addr_match = re.search(
            r"(\d+\s+[^\n]+(?:Hwy|Highway|Rd|Road|St|Street|Ave|Avenue|Dr|Drive|Blvd|Ln|Lane|Way)[^\n]*\n[A-Za-z\s]+,\s*NC\s*\d{5})",
            cell_text,
        )
        address = None
        city = None
        if addr_match:
            address = addr_match.group(1).replace("\n", " ").strip()
            # Extract city from address
            city_match = re.search(r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),\s*NC", address)
            if city_match:
                city = city_match.group(1)

        # Detail page link
        detail_link = cells[0].find("a") or row.find("a")
        detail_url = _URL
        if detail_link and detail_link.get("href"):
            href = detail_link["href"]
            if href.startswith("/"):
                detail_url = f"https://www.hendersoncountync.gov{href}"
            elif href.startswith("http"):
                detail_url = href

        name_key = name.lower()
        if name_key in seen:
            continue
        seen.add(name_key)

        source_id = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
        parks.append({
            "source": "henderson_county",
            "source_id": f"henderson_county_{source_id}",
            "name": name,
            "latitude": None,
            "longitude": None,
            "address": address,
            "city": city or "Hendersonville",
            "county": "Henderson County",
            "phone": None,
            "url": detail_url,
            "amenities": {},
            "extras": {},
        })

    logger.info("henderson_county: fetched %d parks", len(parks))
    return parks


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(message)s")
    parks = fetch()
    print(f"\n{'='*60}")
    print(f"Fetched {len(parks)} Henderson County parks")
    for p in parks:
        addr = p.get("address") or "N/A"
        city = p.get("city") or "N/A"
        print(f"  {p['name']:45s} | {addr:55s} | {city}")