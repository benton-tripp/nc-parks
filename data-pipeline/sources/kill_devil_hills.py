"""Kill Devil Hills parks scraper.

Source: https://www.kdhnc.com/1002/Parks-and-Playgrounds

Unlike other CivicPlus sites, KDH does NOT have a /Facilities endpoint.
Parks are listed on a single static content page — simple requests + BS4.
"""

from __future__ import annotations

import logging
import re

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_URL = "https://www.kdhnc.com/1002/Parks-and-Playgrounds"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; NCParksBot/1.0; +https://github.com/nc-parks)"
}

# Map description phrases to canonical amenity keys
_FEATURE_MAP: dict[str, str] = {
    "fitness trail":        "walking_trails",
    "pond":                 "fishing",
    "mary's paws park":     "dog_park",
    "dog park":             "dog_park",
    "pavilion":             "pavilion",
    "roller hockey rink":   "inline_skating",
    "skateboard ramps":     "skate_park",
    "skate park":           "skate_park",
    "children's play area": "playground",
    "playground":           "playground",
    "playgrounds":          "playground",
    "big kid and toddler playgrounds": "playground",
    "picnic tables":        "picnic_tables",
    "picnic table":         "picnic_tables",
    "picnic shelter with tables": "picnic_shelter",
    "picnic shelter":       "picnic_shelter",
    "benches":              "picnic_tables",
    "swings":               "swings",
    "swing set":            "swings",
    "restrooms":            "restrooms",
    "vehicle parking":      "parking",
    "parking":              "parking",
    "splash pad":           "splash_pad",
    "pickleball/tennis courts": "pickleball",
    "pickleball courts":    "pickleball",
    "tennis courts":        "tennis_courts",
    "large open play field": "open_field",
    "large open field":     "open_field",
    "open field":           "open_field",
    "disc golf":            "disc_golf",
    "sidewalks":            "walking_trails",
    "drop-off circle":      "parking",
}


def _extract_amenities(description: str) -> dict[str, bool]:
    """Parse comma-separated feature descriptions into amenity flags."""
    amenities: dict[str, bool] = {}
    # Normalise and split on commas / "and"
    text = description.lower().strip()
    # Handle negations — remove "no vehicle parking" etc. before splitting
    text = re.sub(r"\bno\s+vehicle\s+parking\b", "", text)
    parts = re.split(r",\s*(?:and\s+)?|\s+and\s+", text)
    for part in parts:
        part = part.strip().rstrip(".")
        if not part:
            continue
        # Try full phrase first, then individual words
        key = _FEATURE_MAP.get(part)
        if key:
            amenities[key] = True
        else:
            # Try matching substrings
            for phrase, akey in _FEATURE_MAP.items():
                if phrase in part:
                    amenities[akey] = True
                    break
    return amenities


def fetch() -> list[dict]:
    """Fetch parks from the KDH static page."""
    resp = requests.get(_URL, headers=_HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    parks: list[dict] = []

    # Each park lives in its own <div class="fr-view"> block.
    for div in soup.find_all("div", class_="fr-view"):
        paragraphs = div.find_all("p")
        if not paragraphs:
            continue

        # First <p> (or <strong> inside it) is the park name
        strong = div.find("strong")
        name = strong.get_text(strip=True) if strong else paragraphs[0].get_text(strip=True)
        if not name or name == "Loading":
            continue

        address = None
        amenities: dict[str, bool] = {}

        for p in paragraphs[1:]:
            text = p.get_text(strip=True)
            if not text:
                continue

            # "Includes ..." line → amenities
            includes_match = re.match(r"(?:.*?\b[Ii]ncludes?\b\s+)(.*)", text)
            if includes_match:
                amenities = _extract_amenities(includes_match.group(1))
                continue

            # Address line: starts with a number or is a known road-type string
            addr_match = re.match(
                r"(\d+\s+.+(?:Drive|Highway|Hwy|Blvd|Boulevard|Ave|Street|St|Road|Rd|Way|Lane|Ln))",
                text,
            )
            if addr_match:
                address = f"{addr_match.group(1).strip()}, Kill Devil Hills, NC 27948"

        source_id = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
        parks.append({
            "source": "kill_devil_hills",
            "source_id": source_id,
            "name": name,
            "latitude": None,
            "longitude": None,
            "address": address,
            "city": "Kill Devil Hills",
            "county": "Dare County",
            "phone": None,
            "url": _URL,
            "amenities": amenities,
            "extras": {},
        })

    logger.info("kill_devil_hills: fetched %d parks", len(parks))
    return parks


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(message)s")
    parks = fetch()
    print(f"\n{'='*60}")
    print(f"Fetched {len(parks)} Kill Devil Hills parks")
    for p in parks:
        amenity_list = [k for k, v in p.get("amenities", {}).items() if v]
        addr = p.get("address") or "N/A"
        print(f"  {p['name']:40s} | {addr:50s} | {amenity_list}")