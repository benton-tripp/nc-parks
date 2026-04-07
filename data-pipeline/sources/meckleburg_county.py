"""Mecklenburg County parks scraper (non-Charlotte towns).

Source: Charlotte Open Data Portal — Parks (ArcGIS Feature Service)
https://data.charlottenc.gov/maps/735a6bce6306442face38657b50fc7b7

Queries the same Mecklenburg County Park and Recreation centroids ArcGIS
endpoint as charlotte.py, but filtered to non-Charlotte cities (Cornelius,
Davidson, Huntersville, Matthews, Mint Hill, Pineville, etc.).
"""

from __future__ import annotations

import logging
import re

import requests

logger = logging.getLogger(__name__)

_QUERY_URL = (
    "https://gis.charlottenc.gov/arcgis/rest/services"
    "/HNS/HousingLocationalToolLayers/MapServer/10/query"
)
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; NCParksBot/1.0; +https://github.com/nc-parks)"
}


def _format_phone(raw: str | None) -> str | None:
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    return raw


def fetch() -> list[dict]:
    params = {
        "where": "CITY <> 'CHARLOTTE' AND PRKSTATUS = 'Developed'",
        "outFields": "PRKNAME,PRKADDR,CITY,ZIP,PRKTYPE,PRKSTATUS,PRKPHONE,PRKADAACC",
        "outSR": 4326,
        "f": "json",
        "resultRecordCount": 2000,
    }

    resp = requests.get(_QUERY_URL, params=params, headers=_HEADERS, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    parks: list[dict] = []
    for feature in data.get("features", []):
        attrs = feature.get("attributes", {})
        geom = feature.get("geometry", {})

        name = (attrs.get("PRKNAME") or "").strip()
        if not name:
            continue

        city = (attrs.get("CITY") or "").strip().title()
        zipcode = attrs.get("ZIP") or ""
        addr_street = (attrs.get("PRKADDR") or "").strip()
        if zipcode:
            address = f"{addr_street}, {city}, NC {zipcode}"
        else:
            address = f"{addr_street}, {city}, NC"

        amenities: dict[str, bool] = {}
        if attrs.get("PRKADAACC"):
            amenities["ada_accessible"] = True

        lat = geom.get("y")
        lon = geom.get("x")

        base_id = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
        source_id = f"mecklenburg_county_{base_id}"
        # Ensure unique source_id when ArcGIS returns multiple features with the same name
        seen_ids = {p["source_id"] for p in parks}
        if source_id in seen_ids:
            suffix = 2
            while f"{source_id}_{suffix}" in seen_ids:
                suffix += 1
            source_id = f"{source_id}_{suffix}"
        parks.append({
            "source": "mecklenburg_county",
            "source_id": source_id,
            "name": name,
            "latitude": lat,
            "longitude": lon,
            "address": address,
            "city": city,
            "county": "Mecklenburg County",
            "phone": _format_phone(attrs.get("PRKPHONE")),
            "url": "https://parkandrec.mecknc.gov/Places-to-Visit/Parks",
            "amenities": amenities,
            "extras": {"park_type": (attrs.get("PRKTYPE") or "").strip().lower()},
        })

    logger.info("mecklenburg_county: fetched %d parks", len(parks))
    return parks


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(message)s")
    parks = fetch()
    print(f"\n{'='*60}")
    print(f"Fetched {len(parks)} Mecklenburg County (non-Charlotte) parks")
    for p in parks:
        coords = f"({p['latitude']:.4f}, {p['longitude']:.4f})" if p.get("latitude") else "N/A"
        print(f"  {p['name']:40s} | {p.get('city',''):15s} | {coords}")