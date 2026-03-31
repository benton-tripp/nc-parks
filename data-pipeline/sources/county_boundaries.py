# From: https://www.nconemap.gov/datasets/fb494670db2144e691c223702ecb30b7_1/api
# https://services.nconemap.gov/secure/rest/services/NC1Map_Regional_Boundaries/MapServer/1/query?where=state%20%3D%20%27NC%27&outFields=*&outSR=4326&f=json

import logging
import requests

logger = logging.getLogger(__name__)

BASE_URL = (
    "https://services.nconemap.gov/secure/rest/services/"
    "NC1Map_Regional_Boundaries/MapServer/1/query"
)

OUT_FIELDS = [
    "county",
    "fips",
    "state_fips",
    "square_mil",
]

PAGE_SIZE = 50  # conservative — polygon geometries are large


def _rings_to_geojson(rings: list[list]) -> dict:
    """Convert ArcGIS polygon rings to a GeoJSON geometry.

    ArcGIS uses the same coordinate format as GeoJSON but wraps them in
    ``rings``.  A single ring → Polygon; multiple rings → Polygon with
    holes (first ring = exterior, rest = holes).  If the service ever
    returns multi-part features we collapse them into a single Polygon
    since county boundaries are typically contiguous.
    """
    if len(rings) == 1:
        return {"type": "Polygon", "coordinates": rings}
    # Multiple rings: first is exterior, remaining are holes
    return {"type": "Polygon", "coordinates": rings}


def _fetch_page(offset: int = 0) -> dict:
    """Fetch a single page of county boundary features."""
    params = {
        "where": "state = 'NC'",
        "outFields": ",".join(OUT_FIELDS),
        "outSR": 4326,
        "f": "json",
        "returnGeometry": "true",
        "resultOffset": offset,
        "resultRecordCount": PAGE_SIZE,
    }
    resp = requests.get(BASE_URL, params=params, timeout=60)
    resp.raise_for_status()
    data = resp.json()

    if "error" in data:
        raise RuntimeError(f"ArcGIS API error: {data['error']}")

    return data


def _parse_feature(feature: dict) -> dict | None:
    """Convert a single ArcGIS feature into a county boundary dict."""
    attrs = feature.get("attributes", {})
    geometry = feature.get("geometry", {})

    county = (attrs.get("county") or attrs.get("COUNTY") or "").strip()
    if not county:
        return None

    rings = geometry.get("rings")
    if not rings:
        logger.warning("Skipping county %r — missing geometry", county)
        return None

    return {
        "county": county,
        "fips": attrs.get("fips") or attrs.get("FIPS"),
        "state_fips": attrs.get("state_fips") or attrs.get("STATE_FIPS"),
        "square_miles": attrs.get("square_mil") or attrs.get("SQUARE_MIL"),
        "geometry": _rings_to_geojson(rings),
    }


def _merge_by_fips(raw: list[dict]) -> list[dict]:
    """Merge multiple features sharing the same FIPS into MultiPolygons.

    Coastal counties (e.g., Pender, New Hanover, Brunswick) are returned
    by the API as separate features for each disconnected land mass.  We
    merge them so we get exactly one record per county.
    """
    from collections import OrderedDict

    merged: OrderedDict[str, dict] = OrderedDict()
    for item in raw:
        fips = item["fips"]
        if fips not in merged:
            merged[fips] = {
                "county": item["county"],
                "fips": fips,
                "state_fips": item["state_fips"],
                "square_miles": item["square_miles"],
                "polygons": [],  # collect all ring sets
            }
        geom = item["geometry"]
        # Each parsed geometry is a Polygon with one or more rings
        merged[fips]["polygons"].append(geom["coordinates"])

    counties = []
    for entry in merged.values():
        polys = entry.pop("polygons")
        if len(polys) == 1:
            entry["geometry"] = {"type": "Polygon", "coordinates": polys[0]}
        else:
            entry["geometry"] = {"type": "MultiPolygon", "coordinates": polys}
        counties.append(entry)

    return counties


def fetch() -> list[dict]:
    """Fetch all NC county boundaries and return a list of county dicts."""
    raw = []
    offset = 0

    while True:
        data = _fetch_page(offset)
        features = data.get("features", [])

        if not features:
            break

        for feature in features:
            parsed = _parse_feature(feature)
            if parsed:
                raw.append(parsed)

        if not data.get("exceededTransferLimit", False):
            break

        offset += len(features)
        logger.info("Fetched %d features so far, continuing…", len(raw))

    counties = _merge_by_fips(raw)
    logger.info("NC county boundaries: %d features → %d counties", len(raw), len(counties))
    return counties


def to_geojson(counties: list[dict] | None = None) -> dict:
    """Return a GeoJSON FeatureCollection of all NC county boundaries.

    If *counties* is ``None``, calls :func:`fetch` automatically.
    """
    if counties is None:
        counties = fetch()

    features = []
    for c in counties:
        features.append({
            "type": "Feature",
            "properties": {
                "county": c["county"],
                "fips": c["fips"],
                "state_fips": c["state_fips"],
                "square_miles": c["square_miles"],
            },
            "geometry": c["geometry"],
        })

    return {
        "type": "FeatureCollection",
        "features": features,
    }


if __name__ == "__main__":
    import json

    logging.basicConfig(level=logging.INFO)
    counties = fetch()
    for c in counties:
        geom = c["geometry"]
        if geom["type"] == "Polygon":
            n_points = sum(len(ring) for ring in geom["coordinates"])
            parts = 1
        else:  # MultiPolygon
            n_points = sum(
                len(ring) for poly in geom["coordinates"] for ring in poly
            )
            parts = len(geom["coordinates"])
        label = f"({parts} parts)" if parts > 1 else ""
        print(f"{c['county']:25s}  FIPS {c['fips']}  "
              f"{c['square_miles']:>8.1f} sq mi  "
              f"{n_points:>6,} vertices {label}")
    print(f"\nTotal: {len(counties)} counties")

    # Write GeoJSON to data/reference/ for use by the pipeline
    from pathlib import Path
    out_dir = Path(__file__).resolve().parents[1] / "data" / "reference"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "nc_counties.geojson"
    geojson = to_geojson(counties)
    with open(out_path, "w") as f:
        json.dump(geojson, f)
    print(f"Wrote {out_path}")