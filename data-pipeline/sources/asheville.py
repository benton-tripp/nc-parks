"""Asheville parks scraper.

Source: https://www.ashevillenc.gov/locations/?avl_department=parks-recreation

Custom WordPress site with all 69 Parks & Recreation locations on a single page.
Each listing has: name (linked), description text, and amenity tags displayed
as text labels (Basketball, Playground, Restrooms, Tennis, etc.).
Also has a Leaflet map with markers, but coordinates are in page JavaScript.
"""

from __future__ import annotations

import logging
import re

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_URL = "https://www.ashevillenc.gov/locations/?avl_department=parks-recreation"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; NCParksBot/1.0; +https://github.com/nc-parks)"
}

# Map tag labels on the page to canonical amenity keys
_TAG_MAP: dict[str, str] = {
    "basketball": "basketball_courts",
    "paved walking path(s)": "walking_trails",
    "unpaved trail(s)": "walking_trails",
    "pickleball": "pickleball",
    "picnic shelter": "picnic_shelter",
    "playground": "playground",
    "restrooms": "restrooms",
    "river access": "boat_ramp",
    "splashpad": "splash_pad",
    "sports field(s)": "sports_fields",
    "tennis": "tennis_courts",
    "unique feature(s)": "special_features",
    "wheelchair accessible": "ada_accessible",
    "outdoor pool": "swimming_pool",
}

# Location type tags
_TYPE_TAGS = {
    "park", "river park", "greenway", "community center",
    "sports complex", "entertainment venue", "pool",
}


def fetch() -> list[dict]:
    resp = requests.get(_URL, headers=_HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    parks: list[dict] = []

    # Each location is an h2 with a link, followed by description paragraph,
    # then tag labels before the next h2.
    headings = soup.find_all("h2")

    for heading in headings:
        link = heading.find("a")
        if not link:
            continue

        name = link.get_text(strip=True)
        if not name:
            continue

        href = link.get("href", "")
        detail_url = href if href.startswith("http") else f"https://www.ashevillenc.gov{href}"

        # Collect text between this h2 and the next h2
        description = ""
        amenities: dict[str, bool] = {}
        location_types: list[str] = []

        sibling = heading.find_next_sibling()
        while sibling and sibling.name != "h2":
            text = sibling.get_text(strip=True)
            if text:
                # Check if this is a description paragraph or tag labels
                # Tags appear as individual text elements after the description
                for tag_label, amenity_key in _TAG_MAP.items():
                    if tag_label in text.lower():
                        amenities[amenity_key] = True

                for type_tag in _TYPE_TAGS:
                    if type_tag in text.lower() and len(text) < 100:
                        location_types.append(type_tag)

                # If text is long enough, it's likely the description
                if len(text) > 50:
                    description = text

            sibling = sibling.find_next_sibling()

        # Also check the heading's parent container for tag text
        parent = heading.find_parent()
        if parent:
            container_text = parent.get_text(" ", strip=True)
            for tag_label, amenity_key in _TAG_MAP.items():
                if tag_label in container_text.lower():
                    amenities[amenity_key] = True

        source_id = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
        parks.append({
            "source": "asheville",
            "source_id": f"asheville_{source_id}",
            "name": name,
            "latitude": None,
            "longitude": None,
            "address": None,
            "city": "Asheville",
            "county": "Buncombe County",
            "phone": None,
            "url": detail_url,
            "amenities": amenities,
            "extras": {"location_types": location_types, "description": description},
        })

    # Try to extract coordinates from page JavaScript (Leaflet markers)
    scripts = soup.find_all("script")
    for script in scripts:
        script_text = script.string or ""
        # Match L.marker([lat, lng]) patterns
        for match in re.finditer(
            r"L\.marker\(\[(-?\d+\.?\d*),\s*(-?\d+\.?\d*)\]",
            script_text,
        ):
            lat = float(match.group(1))
            lon = float(match.group(2))
            # Try to match marker to a park by proximity in script context
            # Look for the park name near this marker definition
            start = max(0, match.start() - 500)
            end = min(len(script_text), match.end() + 500)
            context = script_text[start:end]
            for park in parks:
                if park["name"].lower() in context.lower() and park["latitude"] is None:
                    park["latitude"] = lat
                    park["longitude"] = lon
                    break

    logger.info("asheville: fetched %d locations", len(parks))
    return parks


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(message)s")
    parks = fetch()
    print(f"\n{'='*60}")
    print(f"Fetched {len(parks)} Asheville parks")
    for p in parks:
        amenity_list = sorted(k for k, v in p.get("amenities", {}).items() if v)
        coords = f"({p['latitude']}, {p['longitude']})" if p.get("latitude") else "no coords"
        print(f"  {p['name']:45s} | {coords:25s} | {amenity_list}")