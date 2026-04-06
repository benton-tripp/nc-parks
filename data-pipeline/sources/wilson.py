"""Wilson parks scraper.

Source: https://www.wilsonnc.org/residents/all-departments/parks-recreation/parks-shelters

Granicus CMS with parks in an HTML table, paginated (20 per page).
Columns: Name | Address | Phone.
Site is WAF-protected (returns 403 to requests), so we use Selenium.
"""

from __future__ import annotations

import logging
import re
import time

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_BASE_URL = "https://www.wilsonnc.org/residents/all-departments/parks-recreation/parks-shelters"
PAGE_DELAY = 3


def _get_driver():
    import undetected_chromedriver as uc
    options = uc.ChromeOptions()
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-extensions")
    return uc.Chrome(options=options, version_main=146)


def _parse_page(soup: BeautifulSoup) -> list[dict]:
    """Extract park rows from a single page's table."""
    parks: list[dict] = []
    for row in soup.select("table tr"):
        cells = row.find_all("td")
        if len(cells) < 2:
            continue

        name = cells[0].get_text(strip=True)
        if not name:
            continue

        address_raw = cells[1].get_text(strip=True) if len(cells) > 1 else None
        phone = None
        if len(cells) > 2:
            phone_text = cells[2].get_text(strip=True)
            phone_match = re.search(r"\(?\d{3}\)?\s*[-.]?\s*\d{3}\s*[-.]?\s*\d{4}", phone_text)
            if phone_match:
                phone = phone_match.group(0)

        link = cells[0].find("a")
        detail_url = None
        if link and link.get("href"):
            href = link["href"]
            if href.startswith("/"):
                detail_url = f"https://www.wilsonnc.org{href}"
            elif href.startswith("http"):
                detail_url = href

        source_id = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
        parks.append({
            "source": "wilson",
            "source_id": f"wilson_{source_id}",
            "name": name,
            "latitude": None,
            "longitude": None,
            "address": address_raw,
            "city": "Wilson",
            "county": "Wilson County",
            "phone": phone,
            "url": detail_url or _BASE_URL,
            "amenities": {},
            "extras": {},
        })
    return parks


def fetch() -> list[dict]:
    driver = _get_driver()
    all_parks: list[dict] = []
    seen_ids: set[str] = set()

    try:
        page = 1
        max_pages = 20  # Safety cap

        while page <= max_pages:
            url = _BASE_URL if page == 1 else f"{_BASE_URL}/-npage-{page}"
            logger.info("wilson: fetching page %d -- %s", page, url)

            driver.get(url)
            time.sleep(PAGE_DELAY)

            soup = BeautifulSoup(driver.page_source, "html.parser")

            # On page 1, extract total pages from pager info ("1 - 20 of 38 items")
            if page == 1:
                pager_info = soup.select_one(".pager-info")
                if pager_info:
                    m = re.search(r"of\s+(\d+)\s+items", pager_info.get_text())
                    if m:
                        total = int(m.group(1))
                        max_pages = (total + 19) // 20  # 20 per page
                        logger.info("wilson: %d total items, %d pages", total, max_pages)

            parks = _parse_page(soup)
            if not parks:
                break

            # Deduplicate
            new_count = 0
            for p in parks:
                if p["source_id"] not in seen_ids:
                    seen_ids.add(p["source_id"])
                    all_parks.append(p)
                    new_count += 1

            logger.info("wilson: page %d -> %d new parks (total: %d)", page, new_count, len(all_parks))

            if new_count == 0:
                break

            # Check if there's a non-disabled Next button
            next_btn = soup.select_one("a.pg-next-button:not(.disabled)")
            if not next_btn:
                break

            page += 1
    finally:
        try:
            driver.quit()
        except OSError:
            pass

    logger.info("wilson: fetched %d parks total", len(all_parks))
    return all_parks


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(message)s")
    parks = fetch()
    print(f"\n{'='*60}")
    print(f"Fetched {len(parks)} Wilson parks")
    for p in parks:
        addr = p.get("address") or "N/A"
        phone = p.get("phone") or ""
        print(f"  {p['name']:50s} | {addr:50s} | {phone}")
