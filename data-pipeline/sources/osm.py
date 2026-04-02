"""Fetch parks and playgrounds from OpenStreetMap via the Overpass API.

Queries the entire state of North Carolina using the OSM admin boundary
area filter.  Returns nodes, ways, and relations tagged with leisure=park,
leisure=playground, or leisure=dog_park — with OSM tags mapped to our
normalized amenity keys.

Way geometries are fetched so we can compute polygon area and filter out
non-park features (rooftops, plazas, building courtyards) that are too
small to be real parks.
"""

from __future__ import annotations

import logging
import math
import time
import requests
from shapely.geometry import Point, Polygon
from shapely import STRtree

logger = logging.getLogger(__name__)

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# NC admin boundary relation → Overpass area ID = relation ID + 3_600_000_000
NC_AREA_ID = 3600224045

# We run separate queries to stay under Overpass timeout limits.
# Each tuple: (label, Overpass QL body fragment)
# Ways use "out body geom" to get polygon coordinates for area computation.
# Nodes use "out body" (lat/lon on the element itself).
# Relations use "out body center" (centroid only — too complex for full geom).
_QUERIES = [
    (
        "playgrounds",
        """
        node["leisure"="playground"](area.nc);
        out body qt;
        way["leisure"="playground"](area.nc);
        out body geom qt;
        relation["leisure"="playground"](area.nc);
        out body center qt;
        """,
    ),
    (
        "parks",
        """
        node["leisure"="park"](area.nc);
        out body qt;
        way["leisure"="park"](area.nc);
        out body geom qt;
        relation["leisure"="park"](area.nc);
        out body center qt;
        """,
    ),
    (
        "dog_parks",
        """
        node["leisure"="dog_park"](area.nc);
        out body qt;
        way["leisure"="dog_park"](area.nc);
        out body geom qt;
        relation["leisure"="dog_park"](area.nc);
        out body center qt;
        """,
    ),
]

TIMEOUT_SECONDS = 300  # Overpass query timeout

# Minimum polygon area (m²) for a way tagged leisure=park with no amenities.
# ~2000 m² ≈ 0.5 acres.  Real neighborhood parks are typically 1+ acres.
# Plazas, rooftops, courtyards are well under this.
MIN_PARK_AREA_M2 = 2000

# ---- Child amenity POI queries -------------------------------------------
# These query for features that sit *inside* park boundaries but are tagged
# as separate OSM nodes/ways (not on the park element itself).  After
# collecting parks, we do point-in-polygon checks to enrich park amenities.

_CHILD_AMENITY_QUERIES = [
    (
        "child_playgrounds",
        """
        node["leisure"="playground"](area.nc);
        out body qt;
        way["leisure"="playground"](area.nc);
        out center qt;
        """,
    ),
    (
        "child_pitches",
        """
        node["leisure"="pitch"](area.nc);
        out body qt;
        way["leisure"="pitch"](area.nc);
        out center qt;
        """,
    ),
    (
        "child_amenities",
        """
        node["amenity"="toilets"](area.nc);
        out body qt;
        node["amenity"="drinking_water"](area.nc);
        out body qt;
        node["amenity"="shelter"](area.nc);
        out body qt;
        node["amenity"="bbq"](area.nc);
        out body qt;
        node["amenity"="parking"](area.nc);
        out body qt;
        way["amenity"="parking"](area.nc);
        out center qt;
        way["amenity"="toilets"](area.nc);
        out center qt;
        """,
    ),
    (
        "child_leisure",
        """
        node["leisure"="swimming_pool"](area.nc);
        out body qt;
        way["leisure"="swimming_pool"](area.nc);
        out center qt;
        node["leisure"="picnic_table"](area.nc);
        out body qt;
        node["leisure"="dog_park"](area.nc);
        out body qt;
        way["leisure"="dog_park"](area.nc);
        out center qt;
        node["leisure"="disc_golf_course"](area.nc);
        out body qt;
        way["leisure"="disc_golf_course"](area.nc);
        out center qt;
        node["leisure"="fishing"](area.nc);
        out body qt;
        node["leisure"="skatepark"](area.nc);
        out body qt;
        """,
    ),
]

# Map child POI tags → our canonical amenity keys
def _child_amenity_keys(tags: dict) -> list[str]:
    """Return canonical amenity keys for a child POI based on its tags."""
    keys = []
    leisure = tags.get("leisure", "")
    amenity = tags.get("amenity", "")
    sport = tags.get("sport", "")

    if leisure == "playground":
        keys.append("playground")
    if leisure == "pitch":
        for s in sport.split(";"):
            s = s.strip().lower()
            if s in _SPORT_MAP:
                keys.append(_SPORT_MAP[s])
            elif s:
                keys.append("multipurpose_field")
        if not sport:
            keys.append("multipurpose_field")
    if leisure == "swimming_pool":
        keys.append("swimming_pool")
    if leisure == "picnic_table":
        keys.append("picnic_tables")
    if leisure == "dog_park":
        keys.append("dog_park")
    if leisure == "disc_golf_course":
        keys.append("disc_golf")
    if leisure == "fishing":
        keys.append("fishing")
    if leisure == "skatepark":
        keys.append("skate_park")
    if amenity == "toilets":
        keys.append("restrooms")
    if amenity == "drinking_water":
        keys.append("drinking_water")
    if amenity == "shelter":
        keys.append("picnic_shelter")
    if amenity == "bbq":
        keys.append("bbq_grill")
    if amenity == "parking":
        keys.append("parking")

    return keys

# ---- OSM tag → normalized amenity mapping --------------------------------

# Direct tag key checks (tag present and value is truthy / "yes")
_TAG_AMENITY_MAP = {
    "toilets":          "restrooms",
    "drinking_water":   "drinking_water",
    "covered":          "shaded_areas",
    "shade":            "shaded_areas",
    "lit":              "lighting",
    "wheelchair":       "ada_accessible",
    "dog":              "dog_park",
    "fence":            "fenced_playground",
    "swimming_pool":    "swimming_pool",
    "fishing":          "fishing",
    "shelter":          "picnic_shelter",
    "bench":            "picnic_tables",
    "bbq":              "bbq_grill",
    "camping":          "camping",
}

# Playground-specific sub-tags (playground:*=yes)
_PLAYGROUND_SUB_TAGS = {
    "playground:swing":     "swings",
    "playground:swings":    "swings",
    "playground:slide":     "slides",
    "playground:sandpit":   "sandbox",
    "playground:seesaw":    "seesaw",
    "playground:climbing":  "climbing",
    "playground:zipwire":   "zip_line",
    "playground:roundabout": "merry_go_round",
    "playground:spring":    "spring_rider",
    "playground:basketswing": "swings",
    "playground:structure": "play_structure",
}

# sport=* tag values → amenity keys
_SPORT_MAP = {
    "basketball":       "basketball_courts",
    "tennis":           "tennis_courts",
    "skateboard":       "skate_park",
    "disc_golf":        "disc_golf",
    "baseball":         "ball_fields",
    "softball":         "ball_fields",
    "soccer":           "multipurpose_field",
    "volleyball":       "sand_volleyball",
    "bmx":              "bmx_track",
    "equestrian":       "equestrian",
    "boules":           "bocce",
    "handball":         "handball",
    "horseshoes":       "horseshoe",
    "swimming":         "swimming_pool",
    "multi":            "multipurpose_field",
}


def _map_amenities(tags: dict) -> dict[str, bool]:
    """Extract normalized amenities from OSM tags."""
    amenities: dict[str, bool] = {}

    # leisure type itself tells us something
    leisure = tags.get("leisure", "")
    if leisure == "playground":
        amenities["playground"] = True
    elif leisure == "dog_park":
        amenities["dog_park"] = True

    # Direct tag checks
    for tag_key, amenity_key in _TAG_AMENITY_MAP.items():
        val = tags.get(tag_key, "")
        if val and val.lower() in ("yes", "true", "1"):
            amenities[amenity_key] = True

    # Playground sub-tags
    for tag_key, amenity_key in _PLAYGROUND_SUB_TAGS.items():
        val = tags.get(tag_key, "")
        if val and val.lower() in ("yes", "true", "1"):
            amenities[amenity_key] = True

    # Sport tags (can be semicolon-separated: "basketball;tennis")
    sport = tags.get("sport", "")
    for s in sport.split(";"):
        s = s.strip().lower()
        if s in _SPORT_MAP:
            amenities[_SPORT_MAP[s]] = True

    # Surface / path → walking trails
    if tags.get("highway") in ("path", "footway", "cycleway"):
        amenities["walking_trails"] = True
    if tags.get("surface") and leisure == "park":
        amenities["walking_trails"] = True

    # Parking
    if tags.get("parking") or tags.get("amenity") == "parking":
        amenities["parking"] = True

    return amenities


def _run_overpass(query_body: str, label: str, max_retries: int = 3) -> list[dict]:
    """Execute one Overpass QL query and return the elements.

    Retries with exponential backoff on 429 (rate limit) or 504 (timeout).
    """
    query = f"""
[out:json][timeout:{TIMEOUT_SECONDS}];
area({NC_AREA_ID})->.nc;
{query_body}
"""
    for attempt in range(max_retries):
        if attempt > 0:
            wait = 15 * (2 ** (attempt - 1))  # 15s, 30s, 60s
            logger.info("  Retry %d/%d for [%s] — waiting %ds …",
                        attempt + 1, max_retries, label, wait)
            time.sleep(wait)

        logger.info("  Overpass query [%s] (attempt %d) …", label, attempt + 1)
        resp = requests.post(
            OVERPASS_URL,
            data={"data": query},
            timeout=TIMEOUT_SECONDS + 30,
        )

        if resp.status_code == 429:
            logger.warning("  Rate-limited (429) on [%s]", label)
            continue
        if resp.status_code == 504:
            logger.warning("  Gateway timeout (504) on [%s]", label)
            continue

        resp.raise_for_status()
        data = resp.json()
        elements = data.get("elements", [])
        logger.info("  → %d elements from [%s]", len(elements), label)
        return elements

    # All retries exhausted
    logger.error("  All %d attempts failed for [%s]", max_retries, label)
    return []


def _compute_area_m2(geometry: list[dict]) -> float:
    """Approximate polygon area in m² from a ring of {lat, lon} dicts.

    Uses shapely on lon/lat coordinates with a cos(lat) correction for
    longitude scaling — accurate enough for filtering small features.
    """
    if not geometry or len(geometry) < 3:
        return 0.0
    coords = [(pt["lon"], pt["lat"]) for pt in geometry]
    poly = Polygon(coords)
    if not poly.is_valid or poly.is_empty:
        return 0.0
    centroid = poly.centroid
    lat_rad = math.radians(centroid.y)
    m_per_deg_lat = 111_320
    m_per_deg_lon = 111_320 * math.cos(lat_rad)
    return poly.area * m_per_deg_lat * m_per_deg_lon


def _element_to_park(el: dict, park_polys: dict | None = None) -> dict | None:
    """Convert a single Overpass element to our raw park dict.

    If *park_polys* is provided and the element is a way with valid geometry,
    the Shapely polygon is stored in ``park_polys[source_id]``.

    Applies data-driven filters to exclude non-parks:
      - access=private/customers/no/restricted
      - ownership=private
      - operator:type=private or business
      - building / building:part / height tags (structures, not parks)
      - business amenity tags (bars, restaurants, etc.)
      - Way polygon area < MIN_PARK_AREA_M2 with no recognized amenities
    """
    tags = el.get("tags", {})

    name = tags.get("name")
    if not name:
        return None  # skip unnamed features

    # ---- Data-driven filters ---------------------------------------------

    # 1. Access restrictions
    access = tags.get("access", "")
    if access in ("private", "customers", "no", "restricted"):
        return None

    # 2. Private ownership or operator
    if tags.get("ownership") == "private":
        return None
    if tags.get("operator:type") in ("private", "business"):
        return None

    # 3. Building tags (structures misclassified as parks)
    if any(k.startswith("building") for k in tags) or "height" in tags:
        return None

    # 4. Business amenity tags (breweries, restaurants, etc.)
    _BUSINESS_TAGS = ("bar", "restaurant", "cafe", "pub", "brewery", "fast_food")
    if tags.get("amenity") in _BUSINESS_TAGS:
        return None

    # 5. Museums / purely cultural venues (not parks)
    _TOURISM_SKIP = ("museum", "gallery", "artwork", "theme_park", "attraction")
    if tags.get("tourism") in _TOURISM_SKIP:
        return None

    # ---- Coordinates & area ----------------------------------------------

    area_m2 = None

    if el["type"] == "node":
        lat, lon = el.get("lat"), el.get("lon")
    elif el["type"] == "way":
        # Ways have full geometry from "out body geom"
        geom = el.get("geometry")
        if geom:
            area_m2 = _compute_area_m2(geom)
            # Compute centroid from geometry
            coords = [(pt["lon"], pt["lat"]) for pt in geom]
            poly = Polygon(coords)
            if poly.is_valid and not poly.is_empty:
                lat, lon = poly.centroid.y, poly.centroid.x
            else:
                lat = sum(pt["lat"] for pt in geom) / len(geom)
                lon = sum(pt["lon"] for pt in geom) / len(geom)
        else:
            # Fallback to center if geometry not available
            center = el.get("center", {})
            lat, lon = center.get("lat"), center.get("lon")
    else:
        # Relations use "out body center"
        center = el.get("center", {})
        lat, lon = center.get("lat"), center.get("lon")

    if lat is None or lon is None:
        return None

    amenities = _map_amenities(tags)

    # 5. Area-based filter: small ways with no amenities are plazas/rooftops
    if el["type"] == "way" and area_m2 is not None:
        if area_m2 < MIN_PARK_AREA_M2 and not amenities:
            logger.debug("  Skipped %r — way area %.0f m² < %d, no amenities",
                         name, area_m2, MIN_PARK_AREA_M2)
            return None

    # Build address from addr:* tags
    addr_parts = []
    for key in ("addr:housenumber", "addr:street"):
        if tags.get(key):
            addr_parts.append(tags[key])
    address = " ".join(addr_parts) if addr_parts else None

    city = tags.get("addr:city")
    phone = tags.get("phone") or tags.get("contact:phone")
    url = tags.get("website") or tags.get("contact:website") or tags.get("url")
    operator = tags.get("operator")
    opening_hours = tags.get("opening_hours")

    result = {
        "source": "osm",
        "source_id": f"osm-{el['type'][0]}{el['id']}",
        "name": name,
        "latitude": lat,
        "longitude": lon,
        "address": address,
        "city": city,
        "county": None,  # assigned by enrich step
        "phone": phone,
        "url": url,
        "amenities": amenities,
        "extras": {
            "osm_type": el["type"],
            "osm_id": el["id"],
            "leisure": tags.get("leisure"),
            "operator": operator,
            "opening_hours": opening_hours,
            "access": tags.get("access"),
            "area_m2": round(area_m2, 1) if area_m2 is not None else None,
            "all_tags": {k: v for k, v in tags.items()
                         if not k.startswith("addr:")},
        },
    }

    # Stash polygon for spatial child-amenity matching
    if park_polys is not None and el["type"] == "way":
        geom = el.get("geometry")
        if geom and len(geom) >= 3:
            coords = [(pt["lon"], pt["lat"]) for pt in geom]
            poly = Polygon(coords)
            if poly.is_valid and not poly.is_empty:
                park_polys[result["source_id"]] = poly

    return result
def _enrich_from_child_pois(parks: list[dict], park_polys: dict[str, Polygon]) -> None:
    """Fetch amenity POIs from Overpass and merge into parks via spatial containment.

    For each park that has a polygon, check which child POIs (playgrounds,
    restrooms, pitches, etc.) fall within its boundary, and add those
    amenities to the park record.
    """
    if not park_polys:
        logger.info("No park polygons available — skipping child POI enrichment")
        return

    # Build spatial index: STRtree over park polygons
    source_ids = list(park_polys.keys())
    polys = [park_polys[sid] for sid in source_ids]
    tree = STRtree(polys)

    # Index parks by source_id for fast lookup
    park_by_id = {p["source_id"]: p for p in parks}

    total_enriched = 0
    total_pois = 0

    for label, query_body in _CHILD_AMENITY_QUERIES:
        logger.info("  Pausing 10s before child POI query …")
        time.sleep(10)

        try:
            elements = _run_overpass(query_body, label)
        except requests.RequestException as exc:
            logger.error("Child POI query [%s] failed: %s", label, exc)
            continue

        for el in elements:
            tags = el.get("tags", {})

            # Get point location
            if el["type"] == "node":
                lat, lon = el.get("lat"), el.get("lon")
            else:
                center = el.get("center", {})
                lat, lon = center.get("lat"), center.get("lon")

            if lat is None or lon is None:
                continue

            amenity_keys = _child_amenity_keys(tags)
            if not amenity_keys:
                continue

            total_pois += 1
            pt = Point(lon, lat)

            # Query the spatial index for candidate polygons
            candidates = tree.query(pt)
            for idx in candidates:
                poly = polys[idx]
                if poly.contains(pt):
                    sid = source_ids[idx]
                    park = park_by_id.get(sid)
                    if park:
                        before = len(park["amenities"])
                        for key in amenity_keys:
                            park["amenities"][key] = True
                        if len(park["amenities"]) > before:
                            total_enriched += 1

    logger.info("Child POI enrichment: %d POIs checked, %d parks gained new amenities",
                total_pois, total_enriched)


def fetch() -> list[dict]:
    """Fetch all parks/playgrounds in NC from OpenStreetMap.

    Returns a list of raw park dicts ready for normalize → enrich → dedup.
    """
    seen_ids: set[str] = set()
    parks: list[dict] = []
    park_polys: dict[str, Polygon] = {}  # source_id → Shapely polygon

    for label, query_body in _QUERIES:
        # Pause between queries to be polite to the public Overpass server
        if parks:
            logger.info("  Pausing 10s between Overpass queries …")
            time.sleep(10)

        try:
            elements = _run_overpass(query_body, label)
        except requests.RequestException as exc:
            logger.error("Overpass query [%s] failed: %s", label, exc)
            continue

        for el in elements:
            park = _element_to_park(el, park_polys)
            if park is None:
                continue
            # Deduplicate across query batches (a park can match both
            # leisure=park and leisure=playground)
            if park["source_id"] in seen_ids:
                # Merge amenities from the duplicate hit
                for existing in parks:
                    if existing["source_id"] == park["source_id"]:
                        existing["amenities"].update(park["amenities"])
                        break
                continue
            seen_ids.add(park["source_id"])
            parks.append(park)

    logger.info("OSM total: %d unique named parks/playgrounds in NC "
                "(%d with polygon geometry)", len(parks), len(park_polys))

    # Enrich parks from child OSM features (playgrounds, restrooms, etc.)
    _enrich_from_child_pois(parks, park_polys)

    return parks


# ---- CLI -----------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)s %(message)s")

    results = fetch()
    print(f"\n{'='*60}")
    print(f"Total: {results.__len__()} parks/playgrounds")

    # Quick stats
    with_playground = sum(1 for p in results if p["amenities"].get("playground"))
    with_restrooms = sum(1 for p in results if p["amenities"].get("restrooms"))
    with_swings = sum(1 for p in results if p["amenities"].get("swings"))
    dog_parks = sum(1 for p in results if p["amenities"].get("dog_park"))

    print(f"  Playgrounds:  {with_playground}")
    print(f"  Restrooms:    {with_restrooms}")
    print(f"  Swings:       {with_swings}")
    print(f"  Dog parks:    {dog_parks}")

    # Sample a few
    print(f"\nSample parks:")
    for p in results[:5]:
        amenity_str = ", ".join(k for k, v in p["amenities"].items() if v)
        print(f"  {p['name']} ({p['latitude']:.4f}, {p['longitude']:.4f})")
        print(f"    amenities: {amenity_str or '(none tagged)'}")
