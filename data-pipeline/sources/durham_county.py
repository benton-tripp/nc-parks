"""Durham parks scraper (playgrounds).

Source: https://www.dprplaymore.org/253/Playgrounds

CivicPlus-hosted site for Durham Parks & Recreation.  The Playgrounds page has a
structured HTML table with columns:
  Park Name | Age Range | Swings (Yes/No) | ADA (Yes/No) | Special Features

This gives us 57 playground entries with good structured amenity data.
"""

from __future__ import annotations

import logging
import re

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_URL = "https://www.dprplaymore.org/253/Playgrounds"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; NCParksBot/1.0; +https://github.com/nc-parks)"
}


def _parse_age_range(text: str) -> dict[str, bool]:
    """Convert age range text to amenity flags."""
    amenities: dict[str, bool] = {"playground": True}
    lower = text.lower().strip()
    if "2-5" in lower or "2-12" in lower:
        amenities["toddler_playground"] = True
    return amenities


def _parse_special_features(text: str) -> dict[str, bool]:
    """Extract amenities from the Special Features column."""
    amenities: dict[str, bool] = {}
    lower = text.lower()
    feature_map = {
        "tire swing": "swings",
        "disc swing": "swings",
        "accessible swing": "ada_accessible",
        "unitary surface": "ada_accessible",
        "shaded": "shaded_areas",
        "sprayground": "splash_pad",
        "splash": "splash_pad",
        "fitness": "fitness_equipment",
        "sand pit": "sandbox",
        "nature trail": "walking_trails",
        "fitness trail": "walking_trails",
        "skate": "skate_park",
        "fenced": "fenced_playground",
        "sensory": "sensory_play",
        "pollinator garden": "garden",
    }
    for phrase, key in feature_map.items():
        if phrase in lower:
            amenities[key] = True
    return amenities


def fetch() -> list[dict]:
    resp = requests.get(_URL, headers=_HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    parks: list[dict] = []

    # Find the playground features table
    for row in soup.select("table tr"):
        cells = row.find_all("td")
        if len(cells) < 4:
            continue

        # Column 0: Park Name (may have a link)
        name_cell = cells[0]
        name = name_cell.get_text(strip=True).rstrip("*").strip()
        if not name or name.lower() in ("park name", ""):
            continue

        # Detail page link
        link = name_cell.find("a")
        detail_url = _URL
        if link and link.get("href"):
            href = link["href"]
            if href.startswith("/"):
                detail_url = f"https://www.dprplaymore.org{href}"
            elif href.startswith("http"):
                detail_url = href

        # Column 1: Age Range
        age_range = cells[1].get_text(strip=True) if len(cells) > 1 else ""

        # Column 2: Swings (Yes/No)
        swings_text = cells[2].get_text(strip=True).lower() if len(cells) > 2 else ""

        # Column 3: ADA (Yes/No)
        ada_text = cells[3].get_text(strip=True).lower() if len(cells) > 3 else ""

        # Column 4: Special Features
        features_text = cells[4].get_text(strip=True) if len(cells) > 4 else ""

        # Build amenities
        amenities = _parse_age_range(age_range)
        if swings_text in ("yes", "y"):
            amenities["swings"] = True
        if ada_text in ("yes", "y"):
            amenities["ada_accessible"] = True
        amenities.update(_parse_special_features(features_text))

        source_id = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
        parks.append({
            "source": "durham",
            "source_id": f"durham_{source_id}",
            "name": name,
            "latitude": None,
            "longitude": None,
            "address": None,
            "city": "Durham",
            "county": "Durham County",
            "phone": None,
            "url": detail_url,
            "amenities": amenities,
            "extras": {"age_range": age_range, "special_features": features_text},
        })

    logger.info("durham: fetched %d playgrounds", len(parks))
    return parks


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(message)s")
    parks = fetch()
    print(f"\n{'='*60}")
    print(f"Fetched {len(parks)} Durham playgrounds")
    for p in parks:
        amenity_list = sorted(k for k, v in p.get("amenities", {}).items() if v)
        extras = p.get("extras", {})
        print(f"  {p['name']:45s} | age={extras.get('age_range',''):10s} | {amenity_list}")