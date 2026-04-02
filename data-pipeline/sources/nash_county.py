"""Nash County parks scraper.

Source: https://nashcountync.gov/Facilities

CivicPlus Facility Directory — reuses the shared base class.
Nash County facilities span multiple towns (Nashville, Bailey, Elm City, etc.)
"""

from __future__ import annotations

import logging

from sources.civicplus_base import CivicPlusScraper

logger = logging.getLogger(__name__)


class NashCountyScraper(CivicPlusScraper):
    BASE_URL = "https://nashcountync.gov"
    CITY = "Nashville"  # default city, overridden by address parsing
    COUNTY = "Nash County"
    SOURCE_NAME = "nash_county"

    def _address_cities(self) -> list[str]:
        """Nash County has parks in multiple towns."""
        return [
            "Nashville", "Bailey", "Elm City", "Castalia",
            "Middlesex", "Momeyer", "Red Oak", "Sharpsburg",
            "Spring Hope", "Whitakers", "Rocky Mount",
        ]


_scraper = NashCountyScraper()


def fetch() -> list[dict]:
    return _scraper.fetch()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(message)s")
    parks = fetch()
    print(f"\n{'='*60}")
    print(f"Fetched {len(parks)} Nash County parks")
    for p in parks:
        amenity_list = [k for k, v in p.get("amenities", {}).items() if v]
        addr = p.get("address") or "N/A"
        print(f"  {p['name']:35s} | {addr:45s} | {amenity_list}")