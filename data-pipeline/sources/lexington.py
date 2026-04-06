"""Lexington parks scraper.

Source: https://www.lexingtonnc.gov/city-services/parks-and-recreation/parks-and-facilities

Granicus CMS with tabbed content.  The "PARK LISTING" tab contains a table of
parks with Name and Address columns.  Uses Selenium to render the JS-based
tabs and extract the table data.
"""

from __future__ import annotations

import logging
import re
import time

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_URL = "https://www.lexingtonnc.gov/city-services/parks-and-recreation/parks-and-facilities"
PAGE_DELAY = 4


def _get_driver():
    import undetected_chromedriver as uc
    options = uc.ChromeOptions()
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-extensions")
    return uc.Chrome(options=options, version_main=146)


def _parse_parks(soup: BeautifulSoup) -> list[dict]:
    """Parse parks from the page content."""
    parks: list[dict] = []
    seen: set[str] = set()

    # Strategy 1: Look for table rows with park data
    for row in soup.select("table tr"):
        cells = row.find_all("td")
        if len(cells) < 1:
            continue

        name = cells[0].get_text(strip=True)
        if not name or name.lower() in ("park name", "name", "facility", "park"):
            continue

        address = cells[1].get_text(strip=True) if len(cells) > 1 else None

        # Skip non-park rows (hours, pricing, shelter info, etc.)
        name_low = name.lower()
        if any(kw in name_low for kw in (
            "january", "february", "march", "april", "may", "june",
            "july", "august", "september", "october", "november", "december",
            "school day", "resident", "non resident", "tournament",
            "security deposit", "activity room", "you can",
        )):
            continue
        if re.search(r"\d+:\d+\s*(a\.?m|p\.?m)", name, re.I):
            continue
        if address and "$" in address:
            continue

        if name in seen:
            continue
        seen.add(name)

        # Link
        link = cells[0].find("a")
        detail_url = None
        if link and link.get("href"):
            href = link["href"]
            if href.startswith("/"):
                detail_url = f"https://www.lexingtonnc.gov{href}"
            elif href.startswith("http"):
                detail_url = href

        source_id = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
        parks.append({
            "source": "lexington",
            "source_id": f"lexington_{source_id}",
            "name": name,
            "latitude": None,
            "longitude": None,
            "address": address,
            "city": "Lexington",
            "county": "Davidson County",
            "phone": None,
            "url": detail_url or _URL,
            "amenities": {},
            "extras": {},
        })

    # Strategy 2: If no table found, look for headings/links that are park names
    if not parks:
        content = (
            soup.select_one(".fr-view")
            or soup.select_one("#widget_content")
            or soup.select_one("article")
            or soup
        )
        for heading in content.find_all(["h2", "h3", "h4", "strong"]):
            name = heading.get_text(strip=True)
            if not name or len(name) < 3 or len(name) > 80:
                continue
            if any(skip in name.lower() for skip in [
                "park listing", "shelter", "athletic", "recreation",
                "reservation", "contact", "hours", "welcome", "about",
            ]):
                continue
            if name in seen:
                continue
            seen.add(name)

            # Gather address from siblings
            address = None
            sibling = heading.find_next_sibling()
            if sibling:
                text = sibling.get_text(strip=True)
                addr_match = re.match(r"(\d+\s+.+)", text)
                if addr_match:
                    address = addr_match.group(1).strip()
                    if not re.search(r"Lexington", address, re.I):
                        address += ", Lexington, NC 27292"

            source_id = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
            parks.append({
                "source": "lexington",
                "source_id": f"lexington_{source_id}",
                "name": name,
                "latitude": None,
                "longitude": None,
                "address": address,
                "city": "Lexington",
                "county": "Davidson County",
                "phone": None,
                "url": _URL,
                "amenities": {},
                "extras": {},
            })

    return parks


def fetch() -> list[dict]:
    driver = _get_driver()
    try:
        logger.info("lexington: fetching %s", _URL)
        driver.get(_URL)
        time.sleep(PAGE_DELAY)

        # Try clicking the "PARK LISTING" tab if it exists
        try:
            from selenium.webdriver.common.by import By
            tabs = driver.find_elements(By.CSS_SELECTOR, "[role='tab'], .tab-link, .ui-tabs-anchor")
            for tab in tabs:
                if "park listing" in tab.text.lower():
                    tab.click()
                    time.sleep(2)
                    break
        except Exception as exc:
            logger.debug("lexington: could not click tab: %s", exc)

        soup = BeautifulSoup(driver.page_source, "html.parser")
    finally:
        try:
            driver.quit()
        except OSError:
            pass

    parks = _parse_parks(soup)
    logger.info("lexington: fetched %d parks", len(parks))
    return parks


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(message)s")
    parks = fetch()
    print(f"\n{'='*60}")
    print(f"Fetched {len(parks)} Lexington parks")
    for p in parks:
        addr = p.get("address") or "N/A"
        print(f"  {p['name']:35s} | {addr}")
