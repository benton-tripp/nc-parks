"""Enrich parks with county (and optionally city) via point-in-polygon.

Uses the county boundaries GeoJSON produced by
``sources.county_boundaries`` to assign a county to every park that
doesn't already have one.  Also computes a geohash for downstream
spatial queries.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from shapely.geometry import Point, shape
from shapely.strtree import STRtree

logger = logging.getLogger(__name__)

# Where county_boundaries writes its GeoJSON
_DEFAULT_BOUNDARIES = Path(__file__).resolve().parents[1] / "data" / "reference" / "nc_counties.geojson"

# Simple geohash — enough precision for DynamoDB geo queries
_GEOHASH_PRECISION = 7


def _load_boundaries(path: Path) -> list[tuple[str, any]]:
    """Load county boundary polygons as (county_name, shapely_geometry) pairs."""
    with open(path) as f:
        fc = json.load(f)

    counties = []
    for feature in fc["features"]:
        name = feature["properties"]["county"]
        geom = shape(feature["geometry"])
        counties.append((name, geom))

    logger.info("Loaded %d county boundaries from %s", len(counties), path)
    return counties


def _build_index(counties: list[tuple[str, any]]) -> tuple[STRtree, dict]:
    """Build a spatial R-tree index for fast point-in-polygon lookups."""
    geometries = [geom for _, geom in counties]
    tree = STRtree(geometries)
    # Map geometry id → county name for lookup after query
    geom_to_county = {id(geom): name for name, geom in counties}
    return tree, geom_to_county


def _simple_geohash(lat: float, lon: float, precision: int = _GEOHASH_PRECISION) -> str:
    """Compute a simple geohash string.

    Uses the ``geohash`` approach of interleaving lat/lon bits.  For a
    lightweight implementation without extra dependencies, we use a
    basic base-32 encoding.
    """
    # Encode lat/lon into a single sortable string — enough for range queries.
    # Format: "lat_lon" truncated to requested precision digits.
    # This is a *simplified* geohash; swap in python-geohash if needed.
    lat_norm = (lat + 90) / 180   # 0..1
    lon_norm = (lon + 180) / 360  # 0..1
    lat_int = int(lat_norm * (10 ** precision))
    lon_int = int(lon_norm * (10 ** precision))
    return f"{lon_int:0{precision}d}{lat_int:0{precision}d}"


def enrich(parks: list[dict], boundaries_path: Path | str | None = None) -> list[dict]:
    """Add county and geohash to each park record.

    Parameters
    ----------
    parks:
        Normalized park dicts (from ``processing.normalize``).
    boundaries_path:
        Path to the county boundaries GeoJSON.  Defaults to
        ``data/reference/nc_counties.geojson``.

    Returns
    -------
    list[dict]
        Same parks with ``county`` filled in (if missing) and
        ``geohash`` added.
    """
    boundaries_path = Path(boundaries_path) if boundaries_path else _DEFAULT_BOUNDARIES

    if not boundaries_path.exists():
        logger.warning("County boundaries not found at %s — skipping county enrichment", boundaries_path)
        # Still add geohashes
        for park in parks:
            park["geohash"] = _simple_geohash(park["latitude"], park["longitude"])
        return parks

    counties = _load_boundaries(boundaries_path)
    tree, geom_to_county = _build_index(counties)
    geometries = [geom for _, geom in counties]

    enriched_count = 0
    for park in parks:
        # Always add geohash
        park["geohash"] = _simple_geohash(park["latitude"], park["longitude"])

        # Skip county lookup if already known
        if park.get("county"):
            continue

        point = Point(park["longitude"], park["latitude"])
        result_idx = tree.query(point)

        for idx in result_idx:
            geom = geometries[idx]
            if geom.contains(point):
                park["county"] = geom_to_county[id(geom)]
                enriched_count += 1
                break
        else:
            logger.debug("No county found for %s at (%.4f, %.4f)",
                         park["name"], park["latitude"], park["longitude"])

    logger.info("Enriched %d parks with county data", enriched_count)
    return parks
