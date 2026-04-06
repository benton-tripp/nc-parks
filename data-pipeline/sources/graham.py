"""Graham parks scraper.

Source: https://www.cityofgraham.com/grpd-parks-playgrounds/

WordPress site with all parks on a single page.  Parks grouped under h2 headings
(Community / Neighborhood / Center) with h4 per park, address inline, amenities
extracted from description text.
"""

from __future__ import annotations

import logging
import re

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_URL = "https://www.cityofgraham.com/grpd-parks-playgrounds/"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; NCParksBot/1.0; +https://github.com/nc-parks)"
}

_AMENITY_KEYWORDS: dict[str, str] = {
    "inclusive playground": "ada_accessible",
    "swings":              "swings",
    "slides":              "slides",
    "climbing":            "playground",
    "zipline":             "playground",
    "zip line":            "playground",
    "obstacle course":     "playground",
    "challenge course":    "playground",
    "gaga ball":           "playground",
    "covered seating":     "picnic_shelter",
    "picnic shelter":      "picnic_shelter",
    "shelter":             "picnic_shelter",
    "walking track":       "walking_trails",
    "trail":               "walking_trails",
    "exercise equipment":  "walking_trails",
    "sand volleyball":     "sand_volleyball",
    "volleyball":          "sand_volleyball",
    "bike rack":           "biking",
    "fencing":             "fenced_playground",
    "fenced":              "fenced_playground",
    "green space":         "open_field",
    "playing field":       "multipurpose_field",
    "ada":                 "ada_accessible",
    "accessible":          "ada_accessible",
    "inclusive":            "ada_accessible",
    "shade":               "shaded_areas",
}


def _extract_amenities(description: str) -> dict[str, bool]:
    amenities: dict[str, bool] = {}
    lower = description.lower()
    for keyword, key in _AMENITY_KEYWORDS.items():
        if keyword in lower:
            amenities[key] = True
    return amenities


def fetch() -> list[dict]:
    resp = requests.get(_URL, headers=_HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    parks: list[dict] = []
    content = soup.find("div", class_="entry-content") or soup.find("article") or soup

    for heading in content.find_all("h4"):
        name = heading.get_text(strip=True)
        if not name or name == "Visit a Playground":
            continue

        description_parts = []
        address = None
        sibling = heading.find_next_sibling()
        while sibling and sibling.name not in ("h4", "h2"):
            text = sibling.get_text(strip=True)
            if text:
                description_parts.append(text)
                addr_match = re.search(
                    r"Address:\s*(.+?)(?:\n|$)", sibling.get_text("\n", strip=True)
                )
                if addr_match:
                    address = addr_match.group(1).strip()
            sibling = sibling.find_next_sibling()

        description = " ".join(description_parts)
        amenities = _extract_amenities(description)
        amenities["playground"] = True

        source_id = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
        parks.append({
            "source": "graham",
            "source_id": f"graham_{source_id}",
            "name": name,
            "latitude": None,
            "longitude": None,
            "address": address,
            "city": "Graham",
            "county": "Alamance County",
            "phone": None,
            "url": _URL,
            "amenities": amenities,
            "extras": {},
        })

    logger.info("graham: fetched %d parks", len(parks))
    return parks


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(message)s")
    parks = fetch()
    print(f"\n{'='*60}")
    print(f"Fetched {len(parks)} Graham parks")
    for p in parks:
        amenity_list = sorted(k for k, v in p.get("amenities", {}).items() if v)
        addr = p.get("address") or "N/A"
        print(f"  {p['name']:50s} | {addr:50s} | {amenity_list}")