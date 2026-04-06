"""New Bern parks scraper.

Source: https://www.newbernnc.gov/departments/parks.php

Revize CMS with all parks on a single page grouped by category
(MINI/POCKET, NEIGHBORHOOD, COMMUNITY).  Uses Selenium to render the page,
then parses park names and addresses from the structured HTML content.
"""

from __future__ import annotations

import logging
import re
import time

from bs4 import BeautifulSoup, NavigableString, Tag

logger = logging.getLogger(__name__)

_URL = "https://www.newbernnc.gov/departments/parks.php"
PAGE_DELAY = 4


def _get_driver():
    import undetected_chromedriver as uc
    options = uc.ChromeOptions()
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-extensions")
    return uc.Chrome(options=options, version_main=146)


def _get_address_for_bold(bold: Tag) -> str | None:
    """Extract the address that follows a bold park name.

    Navigate from the <strong> to its parent colored <span>, then walk
    the next siblings looking for address text.  Some parent divs pack
    multiple parks into one font-size <span>; in that case we only take
    the first direct text node before the nested park name.
    """
    colored_span = bold.find_parent("span")
    if not colored_span:
        return None
    for sib in colored_span.next_siblings:
        if isinstance(sib, NavigableString):
            text = sib.strip()
            if text:
                return text
        elif isinstance(sib, Tag):
            if sib.name == "br":
                continue
            if sib.name == "span":
                # If this span nests another park (<strong>), only take
                # the first direct text node before it.
                if sib.find("strong"):
                    for child in sib.children:
                        if isinstance(child, NavigableString):
                            text = child.strip()
                            if text:
                                return text
                        elif isinstance(child, Tag) and child.name == "br":
                            continue
                        else:
                            break
                    return None
                return sib.get_text(strip=True) or None
            break
    return None


def _parse_parks_from_content(soup: BeautifulSoup) -> list[dict]:
    """Parse park names and addresses from the page content.

    The page uses centered divs, each containing:
      <div style="text-align: center;">
        <span style="color: ...;"><strong>ParkName</strong></span>
        <br/>
        <span style="font-size: 14px;">Address</span>
      </div>
    Some divs pack two parks into one font-size span (nested strong tags).
    Category headers (MINI/POCKET, NEIGHBORHOOD, COMMUNITY) are also bold.
    """
    parks: list[dict] = []
    seen: set[str] = set()

    _SKIP_NAMES = {
        "mini/pocket parks", "neighborhood parks", "community parks",
        "regional park", "regional parks", "park type", "parks",
        "phone number", "english",
    }

    for bold in soup.find_all("strong"):
        name = bold.get_text(strip=True)
        if not name or len(name) < 3 or len(name) > 80:
            continue
        if name.lower() in _SKIP_NAMES or name.startswith("Phone"):
            continue

        norm_name = re.sub(r"\s+", " ", name).strip()
        if norm_name in seen:
            continue

        address = _get_address_for_bold(bold)

        seen.add(norm_name)
        source_id = re.sub(r"[^a-z0-9]+", "_", norm_name.lower()).strip("_")
        addr_full = f"{address}, New Bern, NC" if address else None
        parks.append({
            "source": "new_bern",
            "source_id": f"new_bern_{source_id}",
            "name": norm_name,
            "latitude": None,
            "longitude": None,
            "address": addr_full,
            "city": "New Bern",
            "county": "Craven County",
            "phone": None,
            "url": _URL,
            "amenities": {},
            "extras": {},
        })

    return parks


def fetch() -> list[dict]:
    driver = _get_driver()
    try:
        logger.info("new_bern: fetching %s", _URL)
        driver.get(_URL)
        time.sleep(PAGE_DELAY)

        soup = BeautifulSoup(driver.page_source, "html.parser")
    finally:
        try:
            driver.quit()
        except OSError:
            pass

    parks = _parse_parks_from_content(soup)
    logger.info("new_bern: fetched %d parks", len(parks))
    return parks


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(message)s")
    parks = fetch()
    print(f"\n{'='*60}")
    print(f"Fetched {len(parks)} New Bern parks")
    for p in parks:
        addr = p.get("address") or "N/A"
        print(f"  {p['name']:35s} | {addr}")
