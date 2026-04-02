"""Southern Pines parks scraper.

Source: https://www.southernpines.net/Facilities

CivicPlus Facility Directory — reuses the shared base class.
"""

from __future__ import annotations

import logging

from sources.civicplus_base import CivicPlusScraper

logger = logging.getLogger(__name__)


class SouthernPinesScraper(CivicPlusScraper):
    BASE_URL = "https://www.southernpines.net"
    CITY = "Southern Pines"
    COUNTY = "Moore County"
    SOURCE_NAME = "southern_pines"


_scraper = SouthernPinesScraper()


def fetch() -> list[dict]:
    return _scraper.fetch()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(message)s")
    parks = fetch()
    print(f"\n{'='*60}")
    print(f"Fetched {len(parks)} Southern Pines parks")
    for p in parks:
        amenity_list = [k for k, v in p.get("amenities", {}).items() if v]
        addr = p.get("address") or "N/A"
        print(f"  {p['name']:35s} | {addr:45s} | {amenity_list}")