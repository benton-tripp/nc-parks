"""Normalize raw park records from different sources into a common schema.

Every source's ``fetch()`` returns slightly different dicts — different key
names, different amenity representations, etc.  This module maps them all
into a single canonical form so downstream processing doesn't care where a
park came from.

Canonical park schema
---------------------
{
    "source":     str,          # e.g. "wake_county", "osm", "charlotte"
    "source_id":  str,          # unique ID within that source
    "name":       str,
    "latitude":   float,
    "longitude":  float,
    "address":    str | None,
    "city":       str | None,
    "county":     str | None,
    "state":      "NC",
    "phone":      str | None,
    "url":        str | None,
    "amenities":  dict[str, bool],  # normalized amenity key → True/False
    "extras":     dict,             # source-specific fields worth keeping
}
"""

from __future__ import annotations

import logging
import uuid

logger = logging.getLogger(__name__)

# ---- Canonical amenity keys (superset across all sources) ----------------
# Sources map their own field names into these.  Any key a source doesn't
# provide simply won't appear in the dict — that's fine.  ``None`` means
# "unknown" vs. ``False`` = "definitely not present."

CANONICAL_AMENITIES = {
    "playground", "restrooms", "swings", "slides", "splash_pad",
    "shaded_areas", "picnic_tables", "picnic_shelter", "pavilion",
    "ada_accessible", "parking", "drinking_water", "walking_trails",
    "basketball_courts", "tennis_courts", "swimming_pool", "dog_park",
    "disc_golf", "fishing", "boat_rental", "canoe_kayak", "skate_park",
    "greenway_access", "gym", "multipurpose_field", "ball_fields",
    "community_center", "neighborhood_center", "track", "biking",
    "gardens", "camping", "equestrian", "fenced_playground",
    "open_field", "sand_volleyball", "bmx_track", "horseshoe",
    "bocce", "handball", "inline_skating", "carousel", "amusement_train",
    "boat_ride", "arts_center", "environmental_center", "tennis_center",
    "theater", "library", "museum", "live_animals",
}


def normalize(parks: list[dict], source_name: str) -> list[dict]:
    """Normalise a batch of raw parks into canonical form.

    Parameters
    ----------
    parks:
        List of dicts as returned by a source's ``fetch()`` function.
    source_name:
        Identifier for the source (e.g. ``"wake_county"``).  Used to
        select the right mapping logic and stamped into each record.

    Returns
    -------
    list[dict]
        Parks in canonical schema.  Records that can't be normalized
        (missing name or coordinates) are dropped with a warning.
    """
    handler = _SOURCE_HANDLERS.get(source_name, _generic)
    normalized = []

    for raw in parks:
        try:
            park = handler(raw)
        except Exception:
            logger.warning("Failed to normalize record from %s: %s",
                           source_name, raw.get("name", "<unknown>"),
                           exc_info=True)
            continue

        if not park:
            continue

        # Guarantee required fields
        park.setdefault("source", source_name)
        park.setdefault("state", "NC")
        park.setdefault("extras", {})

        if not park.get("name"):
            logger.warning("Dropping park with missing name: %s", park)
            continue

        # Parks need either coordinates or an address (geocoder can resolve later)
        if park.get("latitude") is None and not park.get("address"):
            logger.warning("Dropping park with no coords and no address: %s", park)
            continue

        normalized.append(park)

    logger.info("Normalized %d / %d records from %s",
                len(normalized), len(parks), source_name)
    return normalized


# ---- Source-specific handlers --------------------------------------------

def _wake_county(raw: dict) -> dict | None:
    """Wake County data already closely matches our schema."""
    return {
        "source": "wake_county",
        "source_id": raw.get("source_id", ""),
        "name": raw["name"],
        "latitude": raw["latitude"],
        "longitude": raw["longitude"],
        "address": raw.get("address"),
        "city": None,  # enrichment step fills this in
        "county": raw.get("county", "Wake"),
        "state": "NC",
        "phone": raw.get("phone"),
        "url": raw.get("url"),
        "amenities": raw.get("amenities", {}),
        "extras": {
            "aliases": raw.get("aliases", []),
            "jurisdiction": raw.get("jurisdiction"),
            "notes": raw.get("notes"),
        },
    }


def _osm(raw: dict) -> dict | None:
    """OSM data is already close to canonical — pass through with extras."""
    return {
        "source": "osm",
        "source_id": raw.get("source_id", ""),
        "name": raw.get("name"),
        "latitude": raw.get("latitude"),
        "longitude": raw.get("longitude"),
        "address": raw.get("address"),
        "city": raw.get("city"),
        "county": raw.get("county"),
        "state": "NC",
        "phone": raw.get("phone"),
        "url": raw.get("url"),
        "amenities": raw.get("amenities", {}),
        "extras": raw.get("extras", {}),
    }


def _generic(raw: dict) -> dict | None:
    """Fallback handler — pass through fields that match the schema."""
    return {
        "source": raw.get("source", "unknown"),
        "source_id": raw.get("source_id", str(uuid.uuid4())),
        "name": raw.get("name"),
        "latitude": raw.get("latitude") or raw.get("lat"),
        "longitude": raw.get("longitude") or raw.get("lon"),
        "address": raw.get("address"),
        "city": raw.get("city"),
        "county": raw.get("county"),
        "state": "NC",
        "phone": raw.get("phone"),
        "url": raw.get("url"),
        "amenities": raw.get("amenities", {}),
        "extras": {},
    }


def _johnston_county(raw: dict) -> dict | None:
    """Johnston County scraper data — already close to canonical."""
    return {
        "source": "johnston_county",
        "source_id": raw.get("source_id", ""),
        "name": raw.get("name"),
        "latitude": raw.get("latitude"),
        "longitude": raw.get("longitude"),
        "address": raw.get("address"),
        "city": raw.get("city"),
        "county": raw.get("county", "Johnston"),
        "state": "NC",
        "phone": raw.get("phone"),
        "url": raw.get("url"),
        "amenities": raw.get("amenities", {}),
        "extras": {
            "description": raw.get("description"),
            "hours": raw.get("hours"),
            "accessible": raw.get("accessible"),
            "photos": raw.get("photos", []),
        },
    }


def _alamance_county(raw: dict) -> dict | None:
    """Alamance County scraper data — already close to canonical."""
    return {
        "source": "alamance_county",
        "source_id": raw.get("source_id", ""),
        "name": raw.get("name"),
        "latitude": raw.get("latitude"),
        "longitude": raw.get("longitude"),
        "address": raw.get("address"),
        "city": raw.get("city"),
        "county": raw.get("county", "Alamance"),
        "state": "NC",
        "phone": raw.get("phone"),
        "url": raw.get("url"),
        "amenities": raw.get("amenities", {}),
        "extras": {
            "description": raw.get("description"),
            "hours": raw.get("hours"),
        },
    }


def _greensboro(raw: dict) -> dict | None:
    """Greensboro scraper data — already close to canonical."""
    return {
        "source": "greensboro",
        "source_id": raw.get("source_id", ""),
        "name": raw.get("name"),
        "latitude": raw.get("latitude"),
        "longitude": raw.get("longitude"),
        "address": raw.get("address"),
        "city": raw.get("city", "Greensboro"),
        "county": raw.get("county", "Guilford"),
        "state": "NC",
        "phone": raw.get("phone"),
        "url": raw.get("url"),
        "amenities": raw.get("amenities", {}),
        "extras": raw.get("extras", {}),
    }


def _high_point(raw: dict) -> dict | None:
    """High Point scraper data — already close to canonical."""
    return {
        "source": "high_point",
        "source_id": raw.get("source_id", ""),
        "name": raw.get("name"),
        "latitude": raw.get("latitude"),
        "longitude": raw.get("longitude"),
        "address": raw.get("address"),
        "city": raw.get("city", "High Point"),
        "county": raw.get("county", "Guilford"),
        "state": "NC",
        "phone": raw.get("phone"),
        "url": raw.get("url"),
        "amenities": raw.get("amenities", {}),
        "extras": raw.get("extras", {}),
    }


def _playground_explorers(raw: dict) -> dict:
    """Playground Explorers — already outputs canonical schema."""
    return {
        "source": "playground_explorers",
        "source_id": raw.get("source_id", ""),
        "name": raw.get("name"),
        "latitude": raw.get("latitude"),
        "longitude": raw.get("longitude"),
        "address": raw.get("address"),
        "city": raw.get("city"),
        "county": raw.get("county"),
        "state": "NC",
        "phone": raw.get("phone"),
        "url": raw.get("url"),
        "amenities": raw.get("amenities", {}),
        "extras": raw.get("extras", {}),
    }


# Register handlers per source name
_SOURCE_HANDLERS = {
    "wake_county": _wake_county,
    "osm": _osm,
    "johnston_county": _johnston_county,
    "alamance_county": _alamance_county,
    "greensboro": _greensboro,
    "high_point": _high_point,
    "playground_explorers": _playground_explorers,
    "southern_pines": _generic,
    "nash_county": _generic,
    "kill_devil_hills": _generic,
    # "charlotte": _charlotte,
    # "nc_onemap": _nc_onemap,
}
