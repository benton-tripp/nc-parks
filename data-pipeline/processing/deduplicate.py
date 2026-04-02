"""Deduplicate parks that appear in multiple sources.

Two parks are considered duplicates when they are geographically close
AND have similar names.  When a duplicate is found the records are merged:
the earliest source is kept as primary, and source IDs from all matches
are preserved for future refresh reconciliation.

Also handles:
- Absorbing standalone dog parks into nearby parent parks as amenities
- Tiered distance thresholds (higher name similarity → larger match radius)
"""

from __future__ import annotations

import logging
import math
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

# Tiered distance thresholds — higher name similarity allows a larger radius
# because large parks have centroids hundreds of metres apart across sources.
_DISTANCE_TIERS = [
    (0.90, 500),   # near-exact name → 500m (large park, different centroids)
    (0.75, 300),   # strong match     → 300m
    (0.60, 150),   # moderate match   → 150m
]

# Dog park absorption: merge standalone dog parks into a nearby parent park
# within this radius, adding dog_park=True as an amenity.
DOG_PARK_ABSORPTION_RADIUS_M = 500


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres between two lat/lon points."""
    R = 6_371_000  # Earth radius in metres
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = (math.sin(dphi / 2) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# Common park suffixes/prefixes to strip for comparison
_STRIP_WORDS = {"park", "playground", "memorial", "community", "city",
                "town", "county", "state", "recreation", "area", "center",
                "centre", "the", "of", "at"}


def _core_name(name: str) -> str:
    """Extract the distinctive part of a park name for comparison."""
    words = name.lower().split()
    core = [w for w in words if w not in _STRIP_WORDS]
    return " ".join(core) if core else name.lower()


def _name_similarity(a: str, b: str) -> float:
    """Case-insensitive name similarity with substring awareness.

    If the core of one name is contained in the other (e.g., 'Chavis'
    inside 'John Chavis Memorial Park'), boost the score.
    """
    a_low, b_low = a.lower(), b.lower()
    ratio = SequenceMatcher(None, a_low, b_low).ratio()

    # Substring check on core names (strip common park words)
    core_a, core_b = _core_name(a), _core_name(b)
    if core_a and core_b:
        if core_a in core_b or core_b in core_a:
            # Boost: the distinctive part of one name is inside the other
            # e.g. "Chavis" (from "Chavis Park") in "John Chavis" (from
            # "John Chavis Memorial Park") — almost certainly the same place
            ratio = max(ratio, 0.92)

    return ratio


def _merge_amenities(primary: dict, secondary: dict) -> dict:
    """Merge amenity dicts — True wins over False (more info is better)."""
    merged = dict(primary)
    for key, value in secondary.items():
        if key not in merged or (value is True and merged.get(key) is not True):
            merged[key] = value
    return merged


def _merge_parks(primary: dict, duplicate: dict) -> dict:
    """Merge a duplicate into the primary record."""
    # Track all sources
    sources = primary.get("all_sources", [{"source": primary["source"], "source_id": primary["source_id"]}])
    sources.append({"source": duplicate["source"], "source_id": duplicate["source_id"]})
    primary["all_sources"] = sources

    # Merge amenities — keep whichever has more info
    primary["amenities"] = _merge_amenities(
        primary.get("amenities", {}),
        duplicate.get("amenities", {}),
    )

    # Fill in missing fields from duplicate
    for field in ("address", "city", "county", "phone", "url"):
        if not primary.get(field) and duplicate.get(field):
            primary[field] = duplicate[field]

    return primary


def _is_standalone_dog_park(park: dict) -> bool:
    """True if this park is a dog-park-only entry (not a real park)."""
    leisure = park.get("extras", {}).get("leisure")
    if leisure != "dog_park":
        return False
    amenities = park.get("amenities", {})
    # Has dog_park but no other significant amenities
    meaningful = {k for k, v in amenities.items() if v and k != "dog_park"}
    return len(meaningful) == 0


def _absorb_dog_parks(parks: list[dict]) -> list[dict]:
    """Merge standalone dog parks into nearby parent parks as amenities.

    If a standalone dog park (leisure=dog_park, no other amenities) is
    within DOG_PARK_ABSORPTION_RADIUS_M of a non-dog-park, add dog_park=True
    to the parent and drop the standalone entry.
    """
    dog_parks = [(i, p) for i, p in enumerate(parks) if _is_standalone_dog_park(p)]
    non_dogs = [(i, p) for i, p in enumerate(parks) if not _is_standalone_dog_park(p)]

    absorbed: set[int] = set()

    for di, dp in dog_parks:
        if dp.get("latitude") is None or dp.get("longitude") is None:
            continue
        best_dist = DOG_PARK_ABSORPTION_RADIUS_M + 1
        best_parent_idx = None

        for ni, np_ in non_dogs:
            if np_.get("latitude") is None or np_.get("longitude") is None:
                continue
            dist = _haversine_m(
                dp["latitude"], dp["longitude"],
                np_["latitude"], np_["longitude"],
            )
            if dist < best_dist:
                best_dist = dist
                best_parent_idx = ni

        if best_parent_idx is not None and best_dist <= DOG_PARK_ABSORPTION_RADIUS_M:
            parks[best_parent_idx].setdefault("amenities", {})["dog_park"] = True
            logger.debug(
                "Absorbed dog park %r → %r (%.0fm)",
                dp["name"], parks[best_parent_idx]["name"], best_dist,
            )
            absorbed.add(di)
        # If no parent nearby, the dog park stays as-is

    if absorbed:
        logger.info("Dog park absorption: %d standalone dog parks merged into parent parks", len(absorbed))

    return [p for i, p in enumerate(parks) if i not in absorbed]


def _is_duplicate(park_a: dict, park_b: dict) -> bool:
    """Check if two parks are duplicates using tiered distance/name thresholds."""
    # Can't compare distance without coordinates
    if (park_a.get("latitude") is None or park_a.get("longitude") is None or
            park_b.get("latitude") is None or park_b.get("longitude") is None):
        return False

    dist = _haversine_m(
        park_a["latitude"], park_a["longitude"],
        park_b["latitude"], park_b["longitude"],
    )
    # Quick reject — beyond the largest possible tier
    if dist > _DISTANCE_TIERS[0][1]:
        return False

    sim = _name_similarity(park_a["name"], park_b["name"])

    for min_sim, max_dist in _DISTANCE_TIERS:
        if sim >= min_sim and dist <= max_dist:
            logger.debug(
                "Duplicate: %r ↔ %r (%.0fm, %.0f%% name match)",
                park_a["name"], park_b["name"], dist, sim * 100,
            )
            return True

    return False


def deduplicate(parks: list[dict]) -> list[dict]:
    """Remove duplicate parks from the list.

    Pipeline:
    1. Absorb standalone dog parks into nearby parent parks.
    2. Pairwise deduplication with tiered distance thresholds.

    Parameters
    ----------
    parks:
        Enriched park dicts (all sources combined).

    Returns
    -------
    list[dict]
        Deduplicated parks.  Merged records include an ``all_sources``
        list with every source/source_id pair that contributed.
    """
    if not parks:
        return []

    # Phase 1: absorb standalone dog parks into nearby real parks
    parks = _absorb_dog_parks(parks)

    # Phase 2: pairwise deduplication with tiered thresholds
    merged_into: dict[int, int] = {}  # idx → primary idx

    # O(n²) pairwise comparison — fine for a few thousand parks.
    # If we scale to tens of thousands, bucket by geohash first.
    for i in range(len(parks)):
        if i in merged_into:
            continue
        for j in range(i + 1, len(parks)):
            if j in merged_into:
                continue

            if not _is_duplicate(parks[i], parks[j]):
                continue

            _merge_parks(parks[i], parks[j])
            merged_into[j] = i

    result = [p for i, p in enumerate(parks) if i not in merged_into]
    n_merged = len(merged_into)
    if n_merged:
        logger.info("Deduplication: %d parks → %d (merged %d duplicates)",
                     len(parks), len(result), n_merged)
    else:
        logger.info("Deduplication: %d parks, no duplicates found", len(parks))

    return result
