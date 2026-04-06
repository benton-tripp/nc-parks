"""Fayetteville parks scraper.

Source: https://www.fayettevillenc.gov/Parks-and-Recreation/Parks-Trails

Granicus CMS with parks as card listings, paginated (10 per page).
Each card has: name, address, description, tagged-as categories.
Uses Selenium to bypass Granicus WAF.
"""

from __future__ import annotations

import logging
import re
import time

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_BASE_URL = "https://www.fayettevillenc.gov/Parks-and-Recreation/Parks-Trails"
PAGE_DELAY = 3

_TAG_TO_AMENITY: dict[str, dict[str, bool]] = {
    "dog parks": {"dog_park": True},
    "trails": {"walking_trails": True},
    "neighborhood parks": {},
    "parks": {},
    "special use park": {},
}


def _get_driver():
    import undetected_chromedriver as uc
    options = uc.ChromeOptions()
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-extensions")
    return uc.Chrome(options=options, version_main=146)


def _parse_page(soup: BeautifulSoup) -> list[dict]:
    """Extract park cards from a single page."""
    parks: list[dict] = []

    for card in soup.select("a[href*='/Parks-and-Recreation/Parks-Trails/']"):
        text = card.get_text("\n", strip=True)
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        if not lines:
            continue

        name = lines[0]
        address = None
        description = ""
        tags: list[str] = []

        for line in lines[1:]:
            if re.match(r"^\d+\s+", line) and not address:
                address = line
            elif line.lower().startswith("tagged as:"):
                tag_text = line.split(":", 1)[1].strip()
                tags = [t.strip() for t in tag_text.split(",")]
            else:
                description += " " + line

        amenities: dict[str, bool] = {}
        for tag in tags:
            tag_amenities = _TAG_TO_AMENITY.get(tag.lower(), {})
            amenities.update(tag_amenities)

        href = card.get("href", "")
        detail_url = href if href.startswith("http") else f"https://www.fayettevillenc.gov{href}"

        source_id = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
        parks.append({
            "source": "fayetteville",
            "source_id": f"fayetteville_{source_id}",
            "name": name,
            "latitude": None,
            "longitude": None,
            "address": address,
            "city": "Fayetteville",
            "county": "Cumberland County",
            "phone": None,
            "url": detail_url,
            "amenities": amenities,
            "extras": {"tags": tags, "description": description.strip()},
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
            logger.info("fayetteville: fetching page %d -- %s", page, url)

            driver.get(url)
            time.sleep(PAGE_DELAY)

            soup = BeautifulSoup(driver.page_source, "html.parser")

            # Extract total from pager info on first page
            if page == 1:
                pager_info = soup.select_one(".pager-info")
                if pager_info:
                    m = re.search(r"of\s+(\d+)\s+items", pager_info.get_text())
                    if m:
                        total = int(m.group(1))
                        per_page = 10
                        max_pages = (total + per_page - 1) // per_page
                        logger.info("fayetteville: %d total items, %d pages", total, max_pages)

            parks = _parse_page(soup)
            if not parks:
                break

            new_count = 0
            for p in parks:
                if p["source_id"] not in seen_ids:
                    seen_ids.add(p["source_id"])
                    all_parks.append(p)
                    new_count += 1

            logger.info("fayetteville: page %d -> %d new parks (total: %d)", page, new_count, len(all_parks))

            if new_count == 0:
                break

            next_btn = soup.select_one("a.pg-next-button:not(.disabled)")
            if not next_btn:
                break
            page += 1
    finally:
        try:
            driver.quit()
        except OSError:
            pass

    logger.info("fayetteville: fetched %d parks total", len(all_parks))
    return all_parks


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(message)s")
    parks = fetch()
    print(f"\n{'='*60}")
    print(f"Fetched {len(parks)} Fayetteville parks")
    for p in parks:
        tags = ", ".join(p["extras"].get("tags", []))
        addr = p.get("address") or "N/A"
        print(f"  {p['name']:45s} | {addr:50s} | {tags}")
