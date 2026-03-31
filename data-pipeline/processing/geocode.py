"""Geocode parks — both forward (address → coords) and reverse (coords → address).

Uses OpenStreetMap Nominatim (free, no API key required).
Respects the 1 request/second rate limit per Nominatim usage policy.

Results are cached locally in ``data/reference/geocode_cache.json``
so re-runs don't re-hit the API for already-resolved coordinates.

This step runs right after normalize and BEFORE enrich/dedup, so that
every park has coordinates by the time we need point-in-polygon and
distance calculations.
"""

from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

_CACHE_PATH = Path(__file__).resolve().parents[2] / "data" / "reference" / "geocode_cache.json"

_NOMINATIM_BASE = "https://nominatim.openstreetmap.org"

# Nominatim requires a valid User-Agent identifying the application
_HEADERS = {
    "User-Agent": "NCParksPlaygroundFinder/1.0 (data-pipeline; github.com/nc-parks)",
}

# Nominatim usage policy: max 1 request per second
_REQUEST_DELAY = 1.05  # seconds, slightly over 1s to stay safe


# ── Cache ─────────────────────────────────────────────────────────────────

def _load_cache() -> dict:
    """Load the geocode cache.

    Structure:
        {
            "reverse": {"lat,lon": "address string", ...},
            "forward": {"address string": {"lat": ..., "lon": ...}, ...}
        }
    """
    if _CACHE_PATH.exists():
        with open(_CACHE_PATH) as f:
            cache = json.load(f)
        # Migrate old single-level cache (all reverse entries)
        if "reverse" not in cache and "forward" not in cache:
            cache = {"reverse": cache, "forward": {}}
        logger.info("Loaded geocode cache: %d reverse, %d forward entries",
                    len(cache.get("reverse", {})), len(cache.get("forward", {})))
        return cache
    return {"reverse": {}, "forward": {}}


def _save_cache(cache: dict):
    """Persist the geocode cache."""
    _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_CACHE_PATH, "w") as f:
        json.dump(cache, f, indent=2)
    logger.debug("Saved geocode cache: %d reverse, %d forward entries",
                 len(cache.get("reverse", {})), len(cache.get("forward", {})))


def _reverse_cache_key(lat: float, lon: float) -> str:
    """Consistent cache key from coordinates (5 decimal places ≈ 1m precision)."""
    return f"{lat:.5f},{lon:.5f}"


def _forward_cache_key(address: str) -> str:
    """Consistent cache key from address (lowercased, stripped)."""
    return address.strip().lower()


# ── Nominatim API calls ──────────────────────────────────────────────────

def _call_reverse(lat: float, lon: float, session: requests.Session) -> str | None:
    """Call Nominatim reverse geocode for a single point.

    Returns a formatted address string, or None on failure.
    """
    data = _nominatim_request(session, "reverse", {
        "lat": lat,
        "lon": lon,
        "format": "jsonv2",
        "zoom": 18,
        "addressdetails": 1,
    })

    if not data or "error" in data:
        return None

    addr = data.get("address", {})
    parts = []

    house = addr.get("house_number", "")
    road = addr.get("road", "")
    if road:
        parts.append(f"{house} {road}".strip() if house else road)

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


def _parse_address_parts(address: str) -> dict:
    """Try to split an address into street/city/state for structured search."""
    # Strip zip codes
    addr = re.sub(r'\b\d{5}(-\d{4})?\b', '', address).strip().rstrip(',')
    parts = [p.strip() for p in addr.split(',') if p.strip()]
    result = {}
    if len(parts) >= 3:
        result["street"] = parts[0]
        result["city"] = parts[1]
        result["state"] = parts[2]
    elif len(parts) >= 2:
        result["street"] = parts[0]
        result["city"] = parts[1]
        result["state"] = "North Carolina"
    elif len(parts) == 1:
        result["street"] = parts[0]
        result["state"] = "North Carolina"
    return result


def _nominatim_request(session: requests.Session, endpoint: str,
                       params: dict) -> list | dict | None:
    """Make a Nominatim request with retry on 429."""
    for attempt in range(3):
        try:
            resp = session.get(f"{_NOMINATIM_BASE}/{endpoint}",
                               params=params, headers=_HEADERS, timeout=10)
            if resp.status_code == 429:
                wait = 30 * (attempt + 1)
                logger.warning("Nominatim 429 — waiting %ds before retry", wait)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()
        except (requests.RequestException, ValueError) as exc:
            logger.warning("Nominatim request failed: %s", exc)
            if attempt < 2:
                time.sleep(5)
    return None


def _validate_nc_coords(lat: float, lon: float) -> bool:
    """Check that coordinates are within NC bounds."""
    return 33.5 <= lat <= 37.0 and -85.0 <= lon <= -75.0


def _extract_coords(results: list) -> dict | None:
    """Extract and validate lat/lon from Nominatim search results."""
    if not results:
        return None
    try:
        lat = float(results[0]["lat"])
        lon = float(results[0]["lon"])
    except (KeyError, ValueError, IndexError):
        return None
    if not _validate_nc_coords(lat, lon):
        return None
    return {"lat": lat, "lon": lon}


def _call_forward(address: str, session: requests.Session) -> dict | None:
    """Call Nominatim forward geocode (address → coordinates).

    Tries free-text search first, then falls back to structured search
    (separate street/city/state) which works better for rural addresses.

    Returns {"lat": float, "lon": float} or None on failure.
    """
    # Attempt 1: free-text search
    results = _nominatim_request(session, "search", {
        "q": address,
        "format": "jsonv2",
        "countrycodes": "us",
        "limit": 1,
    })
    coords = _extract_coords(results) if results else None
    if coords:
        return coords

    # Attempt 2: structured search (better for rural roads Nominatim can't parse)
    parts = _parse_address_parts(address)
    if parts.get("street"):
        time.sleep(_REQUEST_DELAY)
        results = _nominatim_request(session, "search", {
            **parts,
            "country": "us",
            "format": "jsonv2",
            "limit": 1,
        })
        coords = _extract_coords(results) if results else None
        if coords:
            logger.debug("Structured search resolved %r", address)
            return coords

    # Attempt 3: search by park name + city (for named places)
    # Strip numbers from the beginning (street addresses) and try as a place name
    name_match = re.match(r'^\d+\s+(.+?)(?:,\s*.+)?$', address)
    if not name_match and parts.get("city"):
        # The address IS a name (no street number) — try name + city
        time.sleep(_REQUEST_DELAY)
        query = f"{parts.get('street', address)}, {parts['city']}, NC"
        results = _nominatim_request(session, "search", {
            "q": query,
            "format": "jsonv2",
            "countrycodes": "us",
            "limit": 1,
        })
        coords = _extract_coords(results) if results else None
        if coords:
            logger.debug("Name-based search resolved %r", address)
            return coords

    logger.debug("Forward geocode failed for %r (all strategies)", address)

    return {"lat": lat, "lon": lon}


# ── Public API ────────────────────────────────────────────────────────────

def geocode(parks: list[dict], batch_size: int = 0) -> list[dict]:
    """Fill in missing coordinates AND missing addresses via Nominatim.

    Runs in two passes:
    1. **Forward** — parks with address but no coords → search for coords
    2. **Reverse** — parks with coords but no address → look up address

    This ensures every park has coordinates (needed for enrich + dedup)
    and as many addresses as possible (nice to have for display).

    Parameters
    ----------
    parks:
        Normalized park dicts. May be missing coordinates, address, or both.
    batch_size:
        Max number of API calls per pass (0 = unlimited). Useful for
        incremental runs.

    Returns
    -------
    list[dict]
        Same parks with coordinates/addresses filled in where possible.
        Parks that still lack coordinates after forward geocoding are
        dropped with a warning (can't be placed on a map).
    """
    cache = _load_cache()
    session = requests.Session()

    # ── Pass 1: Forward geocode (address → coords) ───────────────────
    need_coords = [p for p in parks
                   if p.get("latitude") is None and p.get("address")]
    logger.info("Forward geocoding: %d parks with address but no coords", len(need_coords))

    fwd_api_calls = 0
    fwd_hits = 0
    fwd_cache_hits = 0

    for i, park in enumerate(need_coords):
        if batch_size and fwd_api_calls >= batch_size:
            logger.info("Forward batch limit reached (%d calls). %d parks still unresolved.",
                        batch_size, len(need_coords) - i)
            break

        addr = park["address"]
        # Append ", NC" if not already present to help Nominatim
        query = addr if "nc" in addr.lower() or "north carolina" in addr.lower() \
            else f"{addr}, NC"
        key = _forward_cache_key(query)

        if key in cache["forward"]:
            cached = cache["forward"][key]
            if cached:  # not a cached miss
                park["latitude"] = cached["lat"]
                park["longitude"] = cached["lon"]
                fwd_hits += 1
            fwd_cache_hits += 1
            continue

        time.sleep(_REQUEST_DELAY)
        result = _call_forward(query, session)
        fwd_api_calls += 1

        cache["forward"][key] = result or ""

        if result:
            park["latitude"] = result["lat"]
            park["longitude"] = result["lon"]
            fwd_hits += 1

        if fwd_api_calls % 50 == 0:
            logger.info("  Forward: %d / %d (hits: %d, cache: %d)",
                        fwd_api_calls, len(need_coords), fwd_hits, fwd_cache_hits)
            _save_cache(cache)

    if need_coords:
        logger.info("Forward geocoding: %d API calls, %d cache hits, %d coords resolved",
                    fwd_api_calls, fwd_cache_hits, fwd_hits)

    # Drop parks that STILL have no coordinates (can't be placed on a map)
    before = len(parks)
    parks = [p for p in parks if p.get("latitude") is not None
             and p.get("longitude") is not None]
    dropped = before - len(parks)
    if dropped:
        logger.warning("Dropped %d parks with no coordinates after forward geocoding", dropped)

    # ── Pass 2: Reverse geocode (coords → address) ───────────────────
    need_address = [p for p in parks if not p.get("address")]
    logger.info("Reverse geocoding: %d parks with coords but no address", len(need_address))

    rev_api_calls = 0
    rev_hits = 0
    rev_cache_hits = 0

    for i, park in enumerate(need_address):
        if batch_size and rev_api_calls >= batch_size:
            logger.info("Reverse batch limit reached (%d calls). %d parks still unresolved.",
                        batch_size, len(need_address) - i)
            break

        lat, lon = park["latitude"], park["longitude"]
        key = _reverse_cache_key(lat, lon)

        if key in cache["reverse"]:
            if cache["reverse"][key]:
                park["address"] = cache["reverse"][key]
                rev_hits += 1
            rev_cache_hits += 1
            continue

        time.sleep(_REQUEST_DELAY)
        address = _call_reverse(lat, lon, session)
        rev_api_calls += 1

        cache["reverse"][key] = address or ""

        if address:
            park["address"] = address
            rev_hits += 1

        if rev_api_calls % 50 == 0:
            logger.info("  Reverse: %d / %d (hits: %d, cache: %d)",
                        rev_api_calls, len(need_address), rev_hits, rev_cache_hits)
            _save_cache(cache)

    if need_address:
        logger.info("Reverse geocoding: %d API calls, %d cache hits, %d addresses resolved",
                    rev_api_calls, rev_cache_hits, rev_hits)

    _save_cache(cache)
    return parks


# Keep backward compatibility for any code using the old name
reverse_geocode = geocode
