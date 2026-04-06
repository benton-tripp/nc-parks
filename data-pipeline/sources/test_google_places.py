"""
Test script for Google Places API (New) — REST endpoints.

Performs three operations:
  1. Nearby Search for parks near a point in Raleigh, NC
  2. Text Search for "parks in Asheville NC" with locationRestriction
  3. Place Details (with reviews) for the first result

Usage:
  python -m data-pipeline.sources.test_google_places
"""

import json
import os
import sys
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# Load API key from .env.local
_ENV_FILE = Path(__file__).resolve().parents[2] / ".env.local"


def _load_api_key() -> str:
    if _ENV_FILE.exists():
        for line in _ENV_FILE.read_text().splitlines():
            if line.startswith("GOOGLE_CLOUD_API_KEY="):
                return line.split("=", 1)[1].strip()
    key = os.environ.get("GOOGLE_CLOUD_API_KEY", "")
    if not key:
        sys.exit("ERROR: Set GOOGLE_CLOUD_API_KEY in .env.local or environment")
    return key


API_KEY = _load_api_key()

BASE = "https://places.googleapis.com/v1"

# Raleigh, NC center
RALEIGH = {"latitude": 35.7796, "longitude": -78.6382}

# NC bounding box (approximate)
NC_SW = {"latitude": 33.84, "longitude": -84.32}
NC_NE = {"latitude": 36.59, "longitude": -75.46}


def _headers(*field_paths: str) -> dict:
    """Build request headers with API key and field mask."""
    return {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": ",".join(field_paths),
    }


def _dump(label: str, data: dict):
    print(f"\n{'=' * 60}")
    print(f"  {label}")
    print(f"{'=' * 60}")
    print(json.dumps(data, indent=2, ensure_ascii=False))


# ---------------------------------------------------------------------------
# 1. Nearby Search — parks within 5 km of downtown Raleigh
# ---------------------------------------------------------------------------


def test_nearby_search():
    print("\n[1] Nearby Search — parks within 5 km of downtown Raleigh")

    resp = requests.post(
        f"{BASE}/places:searchNearby",
        headers=_headers(
            "places.id",
            "places.displayName",
            "places.formattedAddress",
            "places.location",
            "places.types",
            "places.rating",
            "places.userRatingCount",
            "places.googleMapsUri",
        ),
        json={
            "includedPrimaryTypes": ["park"],
            "locationRestriction": {
                "circle": {
                    "center": RALEIGH,
                    "radius": 5000.0,
                }
            },
            "maxResultCount": 10,
            "rankPreference": "POPULARITY",
        },
    )
    resp.raise_for_status()
    data = resp.json()
    places = data.get("places", [])
    _dump(f"Nearby Search — {len(places)} parks found", data)
    return places


# ---------------------------------------------------------------------------
# 2. Text Search — "parks in Asheville NC" restricted to NC bounds
# ---------------------------------------------------------------------------


def test_text_search():
    print("\n[2] Text Search — 'parks in Asheville NC'")

    resp = requests.post(
        f"{BASE}/places:searchText",
        headers=_headers(
            "places.id",
            "places.displayName",
            "places.formattedAddress",
            "places.location",
            "places.types",
            "places.rating",
            "places.userRatingCount",
            "places.websiteUri",
            "places.googleMapsUri",
        ),
        json={
            "textQuery": "parks in Asheville NC",
            "includedType": "park",
            "locationRestriction": {
                "rectangle": {
                    "low": NC_SW,
                    "high": NC_NE,
                }
            },
            "pageSize": 10,
        },
    )
    resp.raise_for_status()
    data = resp.json()
    places = data.get("places", [])
    _dump(f"Text Search — {len(places)} parks found", data)
    return places


# ---------------------------------------------------------------------------
# 3. Place Details — reviews + atmosphere for first result
# ---------------------------------------------------------------------------


def test_place_details(place_id: str):
    print(f"\n[3] Place Details + Reviews — {place_id}")

    # Enterprise + Atmosphere fields include reviews, editorialSummary, etc.
    resp = requests.get(
        f"{BASE}/places/{place_id}",
        headers=_headers(
            "id",
            "displayName",
            "formattedAddress",
            "location",
            "types",
            "rating",
            "userRatingCount",
            "regularOpeningHours",
            "websiteUri",
            "googleMapsUri",
            "editorialSummary",
            "reviews",
            "goodForChildren",
            "accessibilityOptions",
            "restroom",
            "allowsDogs",
        ),
        params={"key": API_KEY},
    )
    resp.raise_for_status()
    data = resp.json()
    _dump("Place Details", data)

    # Summarize reviews
    reviews = data.get("reviews", [])
    if reviews:
        print(f"\n  Reviews ({len(reviews)}):")
        for i, r in enumerate(reviews, 1):
            author = r.get("authorAttribution", {}).get("displayName", "?")
            stars = r.get("rating", "?")
            text = (r.get("text", {}).get("text", "") or "")[:120]
            print(f"    {i}. [{stars}★] {author}: {text}...")
    return data


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    print(f"API key loaded: {API_KEY[:10]}...{API_KEY[-4:]}")

    # Nearby Search
    nearby_places = test_nearby_search()

    # Text Search
    text_places = test_text_search()

    # Place Details for first nearby result (or first text result)
    first = (nearby_places or text_places or [None])[0]
    if first:
        place_id = first["id"]
        test_place_details(place_id)
    else:
        print("\nNo places returned — skipping Place Details test.")

    print("\n✓ Done. Check billing at https://console.cloud.google.com/billing")


if __name__ == "__main__":
    main()
