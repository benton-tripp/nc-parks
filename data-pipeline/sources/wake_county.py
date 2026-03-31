# From: https://data-wake.opendata.arcgis.com/search?tags=wakeparks
# API url: https://services1.arcgis.com/a7CWfuGP5ZnLYE7I/arcgis/rest/services/Wake_Parks_Public/FeatureServer/0/query?where=1%3D1&outFields=*&outSR=4326&f=json

import logging
import requests

logger = logging.getLogger(__name__)

BASE_URL = (
    "https://services1.arcgis.com/a7CWfuGP5ZnLYE7I/arcgis/rest/services/"
    "Wake_Parks_Public/FeatureServer/0/query"
)

# All available fields from the Wake County Parks feature layer
OUT_FIELDS = [
    "NAME", "ALIAS1", "ALIAS2", "JURISDICTION", "ADDRESS", "Address2",
    "URL", "PHONE", "Lat", "Lon", "Notes",
    # Amenity flags (1 = yes, 0 / null = no)
    "ARTSCENTER", "BALLFIELDS", "BOATRENTAL", "CANOE", "DISCGOLF",
    "DOGPARK", "ENVCTR", "FISHING", "GREENWAYACCESS", "GYM",
    "MULTIPURPOSEFIELD", "OUTDOORBASKETBALL", "PICNICSHELTER", "PLAYGROUND",
    "POOL", "COMMUNITYCENTER", "NEIGHBORHOODCENTER", "TENNISCOURTS", "TRACK",
    "WALKINGTRAILS", "RESTROOMS", "AMUSEMENTTRAIN", "CAROUSEL", "TENNISCENTER",
    "THEATER", "BOCCE", "HANDBALL", "HORSESHOE", "INLINESKATING",
    "SANDVOLLEYBALL", "SKATEPARK", "ACTIVE_ADULT", "BMXTRACK", "BOATRIDE",
    "LIBRARY", "MUSEUM", "TEEN", "BIKING", "LIVEANIMALS", "GARDENS",
    "EQUESTRIAN", "FORLOCATOR", "CAMPING",
]

# Map ArcGIS field names → normalized amenity keys used in our data model
AMENITY_MAP = {
    "PLAYGROUND":        "playground",
    "RESTROOMS":         "restrooms",
    "PICNICSHELTER":     "picnic_shelter",
    "WALKINGTRAILS":     "walking_trails",
    "BALLFIELDS":        "ball_fields",
    "OUTDOORBASKETBALL":  "basketball_courts",
    "TENNISCOURTS":      "tennis_courts",
    "POOL":              "swimming_pool",
    "DOGPARK":           "dog_park",
    "DISCGOLF":          "disc_golf",
    "FISHING":           "fishing",
    "BOATRENTAL":        "boat_rental",
    "CANOE":             "canoe_kayak",
    "SKATEPARK":         "skate_park",
    "GREENWAYACCESS":    "greenway_access",
    "GYM":               "gym",
    "MULTIPURPOSEFIELD": "multipurpose_field",
    "COMMUNITYCENTER":   "community_center",
    "NEIGHBORHOODCENTER":"neighborhood_center",
    "TRACK":             "track",
    "BIKING":            "biking",
    "GARDENS":           "gardens",
    "CAMPING":           "camping",
    "EQUESTRIAN":        "equestrian",
    "LIVEANIMALS":       "live_animals",
    "CAROUSEL":          "carousel",
    "AMUSEMENTTRAIN":    "amusement_train",
    "BOATRIDE":          "boat_ride",
    "BMXTRACK":          "bmx_track",
    "SANDVOLLEYBALL":    "sand_volleyball",
    "INLINESKATING":     "inline_skating",
    "BOCCE":             "bocce",
    "HANDBALL":          "handball",
    "HORSESHOE":         "horseshoe",
    "ARTSCENTER":        "arts_center",
    "ENVCTR":            "environmental_center",
    "TENNISCENTER":      "tennis_center",
    "THEATER":           "theater",
    "LIBRARY":           "library",
    "MUSEUM":            "museum",
}

PAGE_SIZE = 1000  # ArcGIS default maxRecordCount


def _fetch_page(offset: int = 0) -> dict:
    """Fetch a single page of results from the ArcGIS REST API."""
    params = {
        "where": "1=1",
        "outFields": ",".join(OUT_FIELDS),
        "outSR": 4326,
        "f": "json",
        "resultOffset": offset,
        "resultRecordCount": PAGE_SIZE,
        "returnGeometry": "true",
    }
    resp = requests.get(BASE_URL, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    if "error" in data:
        raise RuntimeError(f"ArcGIS API error: {data['error']}")

    return data


def _parse_amenities(attrs: dict) -> dict[str, bool]:
    """Convert ArcGIS amenity flag fields to a normalized amenities dict."""
    amenities = {}
    for field, key in AMENITY_MAP.items():
        value = attrs.get(field)
        amenities[key] = value == 1 or value == "Yes"
    return amenities


def _parse_feature(feature: dict) -> dict | None:
    """Convert a single ArcGIS feature into a normalized park dict."""
    attrs = feature.get("attributes", {})

    name = (attrs.get("NAME") or "").strip()
    if not name:
        return None

    # Prefer explicit Lat/Lon fields; fall back to geometry
    lat = attrs.get("Lat")
    lon = attrs.get("Lon")
    geom = feature.get("geometry", {})
    if not lat or not lon:
        lon = geom.get("x")
        lat = geom.get("y")

    if lat is None or lon is None:
        logger.warning("Skipping park %r — missing coordinates", name)
        return None

    aliases = list(
        filter(None, [
            (attrs.get("ALIAS1") or "").strip(),
            (attrs.get("ALIAS2") or "").strip(),
        ])
    )

    address_parts = list(dict.fromkeys(filter(None, [
        (attrs.get("ADDRESS") or "").strip(),
        (attrs.get("Address2") or "").strip(),
    ])))

    return {
        "source": "wake_county",
        "source_id": f"wake_{name.lower().replace(' ', '_')}",
        "name": name,
        "aliases": aliases,
        "latitude": float(lat),
        "longitude": float(lon),
        "address": ", ".join(address_parts) if address_parts else None,
        "jurisdiction": (attrs.get("JURISDICTION") or "").strip() or None,
        "phone": (attrs.get("PHONE") or "").strip() or None,
        "url": (attrs.get("URL") or "").strip() or None,
        "notes": (attrs.get("Notes") or "").strip() or None,
        "amenities": _parse_amenities(attrs),
        "county": "Wake",
        "state": "NC",
    }


def fetch() -> list[dict]:
    """Fetch all Wake County parks and return normalized park dicts."""
    parks = []
    offset = 0

    while True:
        data = _fetch_page(offset)
        features = data.get("features", [])

        if not features:
            break

        for feature in features:
            park = _parse_feature(feature)
            if park:
                parks.append(park)

        # ArcGIS signals more pages via exceededTransferLimit
        if not data.get("exceededTransferLimit", False):
            break

        offset += len(features)
        logger.info("Fetched %d parks so far, continuing…", len(parks))

    logger.info("Wake County: fetched %d parks total", len(parks))
    return parks


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = fetch()
    for p in results:
        amenity_list = [k for k, v in p["amenities"].items() if v]
        print(f"{p['name']:40s} ({p['latitude']:.4f}, {p['longitude']:.4f})  "
              f"amenities: {', '.join(amenity_list) or 'none'}")
    print(f"\nTotal: {len(results)} parks")
