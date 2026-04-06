"""
Google Places API (New) — tiled discovery of parks & playgrounds across NC.

Uses Text Search with IDs-only field mask (FREE tier) to discover place IDs,
then a second pass with Pro fields to get name/address/location/types.

Discovery tiles NC with 0.25° rectangles and paginates each tile (max 60
results per query).  Results are deduplicated by place ID across tiles.

Usage:
    # Discovery only — writes raw JSON to data/raw/
    python -m data-pipeline.sources.google_places

    # Dry-run — show tile grid without calling API
    python -m data-pipeline.sources.google_places --dry-run
"""

import json
import logging
import math
import os
import sys
import time
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

_ENV_FILE = Path(__file__).resolve().parents[2] / ".env.local"

BASE = "https://places.googleapis.com/v1"

# NC bounding box (generous — actual land filtered by results)
NC_LAT_MIN, NC_LAT_MAX = 33.84, 36.59
NC_LON_MIN, NC_LON_MAX = -84.32, -75.46

TILE_SIZE_LAT = 0.25  # ~28 km
TILE_SIZE_LON = 0.25  # ~23 km

# Types to search — run separately and merge
PLACE_TYPES = ["park", "playground"]

# Text Search returns max 20 per page, 60 total (3 pages)
PAGE_SIZE = 20

# Rate limiting — Google allows 600 QPM for Places API
REQUEST_DELAY = 0.15  # seconds between requests


def _load_api_key() -> str:
    if _ENV_FILE.exists():
        for line in _ENV_FILE.read_text().splitlines():
            if line.startswith("GOOGLE_CLOUD_API_KEY="):
                return line.split("=", 1)[1].strip()
    key = os.environ.get("GOOGLE_CLOUD_API_KEY", "")
    if not key:
        sys.exit("ERROR: Set GOOGLE_CLOUD_API_KEY in .env.local or environment")
    return key


# ---------------------------------------------------------------------------
# Tile generation
# ---------------------------------------------------------------------------


def generate_tiles() -> list[dict]:
    """Generate a grid of rectangles covering NC."""
    tiles = []
    lat = NC_LAT_MIN
    while lat < NC_LAT_MAX:
        lon = NC_LON_MIN
        while lon < NC_LON_MAX:
            tiles.append({
                "low": {
                    "latitude": lat,
                    "longitude": lon,
                },
                "high": {
                    "latitude": min(lat + TILE_SIZE_LAT, NC_LAT_MAX),
                    "longitude": min(lon + TILE_SIZE_LON, NC_LON_MAX),
                },
            })
            lon += TILE_SIZE_LON
        lat += TILE_SIZE_LAT
    return tiles


# ---------------------------------------------------------------------------
# API calls
# ---------------------------------------------------------------------------


def _headers(field_paths: list[str], api_key: str) -> dict:
    return {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": ",".join(field_paths),
    }


# Field sets by billing tier
FIELDS_FREE: list[str] = []  # IDs only — $0
FIELDS_PRO: list[str] = [
    "places.displayName",
    "places.formattedAddress",
    "places.location",
    "places.types",
    "places.rating",
    "places.userRatingCount",
    "places.websiteUri",
    "places.googleMapsUri",
    "places.accessibilityOptions",
]


def _text_search_page(
    api_key: str,
    text_query: str,
    included_type: str,
    tile: dict,
    page_token: str | None = None,
    extra_fields: list[str] | None = None,
) -> dict:
    """Execute one page of a Text Search request."""
    body = {
        "textQuery": text_query,
        "includedType": included_type,
        "locationRestriction": {"rectangle": tile},
        "pageSize": PAGE_SIZE,
    }
    if page_token:
        body["pageToken"] = page_token

    fields = ["places.id", "nextPageToken"] + (extra_fields or [])

    resp = requests.post(
        f"{BASE}/places:searchText",
        headers=_headers(fields, api_key),
        json=body,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def search_tile(
    api_key: str,
    text_query: str,
    included_type: str,
    tile: dict,
    tile_label: str,
    extra_fields: list[str] | None = None,
) -> list[dict]:
    """Search all pages for a single tile. Returns list of place dicts."""
    places = []
    page_token = None
    page_num = 0

    while True:
        page_num += 1
        data = _text_search_page(api_key, text_query, included_type, tile, page_token, extra_fields)
        batch = data.get("places", [])
        places.extend(batch)

        page_token = data.get("nextPageToken")
        if not page_token or not batch:
            break

        logger.debug("  %s page %d: %d results, continuing…", tile_label, page_num, len(batch))
        time.sleep(REQUEST_DELAY)

    return places


# ---------------------------------------------------------------------------
# Main discovery
# ---------------------------------------------------------------------------


def fetch(pro: bool = False) -> list[dict]:
    """Discover parks & playgrounds across NC via tiled Text Search.

    Args:
        pro: If True, request Pro-tier fields (name, address, location, etc.)
             ~$28 per full run. If False, IDs only (free).

    Returns a list of normalized park dicts ready for the pipeline.
    """
    extra_fields = FIELDS_PRO if pro else FIELDS_FREE
    tier = "Pro (~$28)" if pro else "IDs-only (FREE)"
    api_key = _load_api_key()
    tiles = generate_tiles()
    logger.info("Generated %d tiles covering NC — billing tier: %s", len(tiles), tier)

    # Collect all raw results keyed by place ID for dedup
    seen: dict[str, dict] = {}

    for place_type in PLACE_TYPES:
        text_query = f"{place_type}s in North Carolina"
        logger.info("Searching for '%s' (type=%s) across %d tiles…",
                     text_query, place_type, len(tiles))

        for i, tile in enumerate(tiles):
            tile_label = (
                f"[{place_type}] tile {i + 1}/{len(tiles)} "
                f"({tile['low']['latitude']:.2f},{tile['low']['longitude']:.2f})"
            )

            try:
                places = search_tile(api_key, text_query, place_type, tile, tile_label, extra_fields)
            except requests.HTTPError as e:
                logger.warning("  %s FAILED: %s", tile_label, e)
                time.sleep(1)
                continue

            new_count = 0
            for p in places:
                pid = p["id"]
                if pid not in seen:
                    seen[pid] = p
                    new_count += 1

            if places:
                logger.info("  %s: %d results (%d new, %d total unique)",
                            tile_label, len(places), new_count, len(seen))

            time.sleep(REQUEST_DELAY)

    logger.info("Discovery complete: %d unique places found", len(seen))

    # Convert to pipeline-compatible dicts
    return [_to_park_dict(p) for p in seen.values()]


def _to_park_dict(place: dict) -> dict:
    """Convert a Google Places API result to our canonical park dict."""
    loc = place.get("location", {})
    display = place.get("displayName", {})
    types = place.get("types", [])
    accessibility = place.get("accessibilityOptions", {})

    amenities = {}
    # Infer amenities from Google place types
    type_amenity_map = {
        "playground": "playground",
        "dog_park": "dog_park",
        "campground": "camping",
        "swimming_pool": "swimming_pool",
        "golf_course": "golf",
        "gym": "gym",
        "sports_complex": "sports_complex",
        "athletic_field": "ball_fields",
        "hiking_area": "walking_trails",
        "marina": "boat_rental",
        "fishing_charter": "fishing",
        "ski_resort": "ski",
        "botanical_garden": "gardens",
        "zoo": "live_animals",
        "wildlife_park": "live_animals",
    }
    for gtype, amenity_key in type_amenity_map.items():
        if gtype in types:
            amenities[amenity_key] = True

    if accessibility.get("wheelchairAccessibleEntrance"):
        amenities["wheelchair_accessible"] = True

    return {
        "source": "google_places",
        "source_id": place["id"],
        "name": display.get("text", "Unknown"),
        "latitude": loc.get("latitude"),
        "longitude": loc.get("longitude"),
        "address": place.get("formattedAddress"),
        "city": None,  # will be enriched by pipeline
        "county": None,  # will be enriched by pipeline
        "state": "NC",
        "phone": None,
        "url": place.get("websiteUri"),
        "amenities": amenities,
        "extras": {
            "google_place_id": place["id"],
            "google_maps_uri": place.get("googleMapsUri"),
            "google_rating": place.get("rating"),
            "google_rating_count": place.get("userRatingCount"),
            "google_types": types,
        },
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Google Places NC park discovery")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show tile grid without calling API")
    tier = parser.add_mutually_exclusive_group()
    tier.add_argument("--free", action="store_true", default=True,
                      help="IDs-only field mask — $0 cost (default)")
    tier.add_argument("--pro", action="store_true",
                      help="Pro field mask (name, address, coords, etc.) — ~$28/run")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    if args.dry_run:
        tiles = generate_tiles()
        print(f"Tile grid: {math.ceil((NC_LAT_MAX - NC_LAT_MIN) / TILE_SIZE_LAT)} rows "
              f"x {math.ceil((NC_LON_MAX - NC_LON_MIN) / TILE_SIZE_LON)} cols "
              f"= {len(tiles)} tiles")
        print(f"Place types: {PLACE_TYPES}")
        print(f"Max requests: {len(tiles) * len(PLACE_TYPES) * 3} "
              f"(if every tile paginates 3 pages)")
        print(f"Estimated time: ~{len(tiles) * len(PLACE_TYPES) * 1.3 * REQUEST_DELAY / 60:.1f} min")
        sys.exit(0)

    results = fetch(pro=args.pro)

    # ── Save to disk FIRST ──
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%dT%H%M%S")
    out_dir = Path(__file__).resolve().parents[2] / "data" / "raw"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"google_places_{ts}.json"
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nSaved {len(results)} results → {out_path}")

    # Summary
    rated = [p for p in results if p["extras"].get("google_rating")]
    avg_rating = sum(p["extras"]["google_rating"] for p in rated) / len(rated) if rated else 0

    print(f"\n{'=' * 60}")
    print(f"  Google Places Discovery — {len(results)} unique places")
    print(f"{'=' * 60}")
    print(f"  With ratings: {len(rated)}")
    print(f"  Avg rating:   {avg_rating:.2f}")

    # Top 20 by review count
    by_reviews = sorted(results, key=lambda p: p["extras"].get("google_rating_count") or 0, reverse=True)
    print(f"\n  Top 20 by review count:")
    for p in by_reviews[:20]:
        rc = p["extras"].get("google_rating_count") or 0
        r = p["extras"].get("google_rating") or 0
        print(f"    {p['name']:45s} {r:.1f}★ ({rc:,} reviews)  {p['address'] or ''}")

    print(f"\n  Sample types distribution:")
    type_counts: dict[str, int] = {}
    for p in results:
        for t in p["extras"].get("google_types", []):
            type_counts[t] = type_counts.get(t, 0) + 1
    for t, c in sorted(type_counts.items(), key=lambda x: -x[1])[:15]:
        print(f"    {t:30s} {c}")
