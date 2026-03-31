"""Reverse geocode parks that have no address.

Uses OpenStreetMap Nominatim (free, no API key required).
Respects the 1 request/second rate limit per Nominatim usage policy.

Results are cached locally in ``data/reference/geocode_cache.json``
so re-runs don't re-hit the API for already-resolved coordinates.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

_CACHE_PATH = Path(__file__).resolve().parents[1] / "data" / "reference" / "geocode_cache.json"

_NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"

# Nominatim requires a valid User-Agent identifying the application
_HEADERS = {
    "User-Agent": "NCParksPlaygroundFinder/1.0 (data-pipeline; github.com/nc-parks)",
}

# Nominatim usage policy: max 1 request per second
_REQUEST_DELAY = 1.05  # seconds, slightly over 1s to stay safe


def _load_cache() -> dict[str, str]:
    """Load the geocode cache (keyed by 'lat,lon' → address string)."""
    if _CACHE_PATH.exists():
        with open(_CACHE_PATH) as f:
            cache = json.load(f)
        logger.info("Loaded geocode cache: %d entries", len(cache))
        return cache
    return {}


def _save_cache(cache: dict[str, str]):
    """Persist the geocode cache."""
    _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_CACHE_PATH, "w") as f:
        json.dump(cache, f, indent=2)
    logger.debug("Saved geocode cache: %d entries", len(cache))


def _cache_key(lat: float, lon: float) -> str:
    """Consistent cache key from coordinates (5 decimal places ≈ 1m precision)."""
    return f"{lat:.5f},{lon:.5f}"


def _reverse_geocode(lat: float, lon: float, session: requests.Session) -> str | None:
    """Call Nominatim reverse geocode for a single point.

    Returns a formatted address string, or None on failure.
    """
    params = {
        "lat": lat,
        "lon": lon,
        "format": "jsonv2",
        "zoom": 18,  # building-level detail
        "addressdetails": 1,
    }

    try:
        resp = session.get(_NOMINATIM_URL, params=params, headers=_HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError) as exc:
        logger.warning("Nominatim request failed for (%.5f, %.5f): %s", lat, lon, exc)
        return None

    if "error" in data:
        logger.debug("Nominatim returned error for (%.5f, %.5f): %s", lat, lon, data["error"])
        return None

    # Build a clean street address from the address components
    addr = data.get("address", {})
    parts = []

    # Street address: house_number + road
    house = addr.get("house_number", "")
    road = addr.get("road", "")
    if road:
        parts.append(f"{house} {road}".strip() if house else road)

    # City: look for city, town, village, hamlet in that order
    city = (addr.get("city") or addr.get("town")
            or addr.get("village") or addr.get("hamlet") or "")
    if city:
        parts.append(city)

    state = addr.get("state", "")
    postcode = addr.get("postcode", "")

    if state and postcode:
        parts.append(f"{state} {postcode}")
    elif state:
        parts.append(state)

    return ", ".join(parts) if parts else None


def reverse_geocode(parks: list[dict], batch_size: int = 0) -> list[dict]:
    """Fill in missing addresses via Nominatim reverse geocoding.

    Parameters
    ----------
    parks:
        Park dicts. Only those with a falsy ``address`` are geocoded.
    batch_size:
        Max number of API calls to make (0 = unlimited).  Useful for
        incremental runs when you don't want to wait for 1,800+ lookups.

    Returns
    -------
    list[dict]
        Same parks list with ``address`` filled in where possible.
    """
    cache = _load_cache()
    session = requests.Session()

    need_geocode = [p for p in parks if not p.get("address")]
    logger.info("Parks needing geocode: %d / %d total", len(need_geocode), len(parks))

    if not need_geocode:
        return parks

    hits = 0
    api_calls = 0
    cache_hits = 0

    for i, park in enumerate(need_geocode):
        if batch_size and api_calls >= batch_size:
            logger.info("Batch limit reached (%d calls). %d parks still unresolved.",
                        batch_size, len(need_geocode) - i)
            break

        lat, lon = park["latitude"], park["longitude"]
        key = _cache_key(lat, lon)

        # Check cache first
        if key in cache:
            if cache[key]:  # cached address (not a cached miss)
                park["address"] = cache[key]
                hits += 1
            cache_hits += 1
            continue

        # Rate limit
        time.sleep(_REQUEST_DELAY)

        address = _reverse_geocode(lat, lon, session)
        api_calls += 1

        # Cache the result (including None to avoid re-querying known misses)
        cache[key] = address or ""

        if address:
            park["address"] = address
            hits += 1

        if api_calls % 50 == 0:
            logger.info("  Geocoded %d / %d (hits: %d, cache: %d)",
                        api_calls, len(need_geocode), hits, cache_hits)
            _save_cache(cache)  # periodic save

    _save_cache(cache)
    logger.info("Geocoding complete: %d API calls, %d cache hits, %d addresses resolved",
                api_calls, cache_hits, hits)

    return parks
