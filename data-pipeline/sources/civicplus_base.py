"""Reusable CivicPlus Facility Directory scraper base.

Many NC municipalities use CivicPlus CMS with the same Facility Directory
module.  This module provides a base class with shared Selenium pagination,
detail page parsing, and feature extraction logic.

Subclasses override:
  - BASE_URL, CITY, COUNTY
  - FEATURE_MAP additions (merges with the shared map)
  - SKIP_KEYWORDS additions
  - _address_regexp() for city-specific address patterns
"""

from __future__ import annotations

import logging
import re
import time

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; NCParksBot/1.0; +https://github.com/nc-parks)"
}

REQUEST_DELAY = 0.5  # seconds between detail page fetches

# Shared feature text → normalized amenity key mapping
# Covers common CivicPlus facility feature strings across multiple sites.
SHARED_FEATURE_MAP: dict[str, str] = {
    "ada accessible":               "ada_accessible",
    "basketball court(s)":          "basketball_courts",
    "basketball courts":            "basketball_courts",
    "basketball court":             "basketball_courts",
    "batting cages":                "ball_fields",
    "disc golf":                    "disc_golf",
    "disc golf course":             "disc_golf",
    "dog park":                     "dog_park",
    "fishing":                      "fishing",
    "greenway access":              "greenway_access",
    "lighted athletic field(s)":    "ball_fields",
    "lighted fields":               "ball_fields",
    "multipurpose athletic field(s)": "multipurpose_field",
    "multipurpose field":           "multipurpose_field",
    "multi-purpose field":          "multipurpose_field",
    "multipurpose room(s)":         "community_center",
    "nature trail(s)":              "walking_trails",
    "nature trail":                 "walking_trails",
    "outdoor pool":                 "swimming_pool",
    "pool":                         "swimming_pool",
    "swimming pool":                "swimming_pool",
    "pickleball courts":            "pickleball",
    "pickleball":                   "pickleball",
    "picnic shelters":              "picnic_shelter",
    "picnic shelter(s)":            "picnic_shelter",
    "picnic shelter":               "picnic_shelter",
    "picnic area":                  "picnic_tables",
    "picnic tables":                "picnic_tables",
    "playground":                   "playground",
    "playground/play equipment":    "playground",
    "play equipment":               "playground",
    "restrooms":                    "restrooms",
    "restroom":                     "restrooms",
    "sand volleyball":              "sand_volleyball",
    "volleyball court":             "sand_volleyball",
    "skate park":                   "skate_park",
    "splash pad":                   "splash_pad",
    "tennis court(s)":              "tennis_courts",
    "tennis courts":                "tennis_courts",
    "tennis court":                 "tennis_courts",
    "lighted tennis courts":        "tennis_courts",
    "walking trail(s)":             "walking_trails",
    "walking trails":               "walking_trails",
    "walking trail":                "walking_trails",
    "walking track":                "walking_trails",
    "youth baseball field":         "ball_fields",
    "youth baseball field(s)":      "ball_fields",
    "youth softball field(s)":      "ball_fields",
    "baseball field(s)":            "ball_fields",
    "baseball fields":              "ball_fields",
    "softball field(s)":            "ball_fields",
    "soccer field(s)":              "multipurpose_field",
    "soccer fields":                "multipurpose_field",
    "amphitheater":                 "theater",
    "boat launch/pier":             "boat_rental",
    "boat ramp":                    "boat_rental",
    "canoe/kayak launch":           "canoe_kayak",
    "concessions":                  "concessions",
    "concession stand":             "concessions",
    "gymnasium":                    "gym",
    "gym":                          "gym",
    "horseshoe pits":               "horseshoe",
    "horseshoes":                   "horseshoe",
    "lake access":                  "fishing",
    "senior center":                "community_center",
    "community center":             "community_center",
    "community building":           "community_center",
    "sheltered picnic tables":      "picnic_shelter",
    "open play area":               "open_field",
    "open field":                   "open_field",
    "fitness trail":                "walking_trails",
    "fitness stations":             "walking_trails",
    "exercise stations":            "walking_trails",
    "gardens":                      "gardens",
    "garden":                       "gardens",
    "gazebo":                       "pavilion",
    "pavilion":                     "pavilion",
    "grills":                       "bbq_grill",
    "grill":                        "bbq_grill",
    "bbq grills":                   "bbq_grill",
    "parking":                      "parking",
    "bike rack":                    "biking",
    "bicycle repair station":       "biking",
    "t-ball field":                 "ball_fields",
    "football field":               "multipurpose_field",
    "track":                        "track",
    "running track":                "track",
    "golf practice area":           "golf",
    "golf course":                  "golf",
    "miniature golf":               "golf",
    "lighting":                     "lighting",
}

# Common non-park facility keywords
SHARED_SKIP_KEYWORDS = frozenset({
    "library", "conference room", "city hall", "municipal building",
    "museum", "blacksmith", "theater", "theatre", "classroom",
    "education", "collection center", "landfill", "compost",
    "lecture gallery", "meeting house", "store", "administration",
})


class CivicPlusScraper:
    """Base scraper for CivicPlus Facility Directory sites."""

    # Subclass must set these
    BASE_URL: str = ""       # e.g. "https://www.highpointnc.gov"
    CITY: str = ""           # e.g. "High Point"
    COUNTY: str = ""         # e.g. "Guilford County"
    SOURCE_NAME: str = ""    # e.g. "high_point"

    # Subclass can extend
    EXTRA_FEATURE_MAP: dict[str, str] = {}
    EXTRA_SKIP_KEYWORDS: frozenset[str] = frozenset()

    def __init__(self):
        self._feature_map = {**SHARED_FEATURE_MAP, **self.EXTRA_FEATURE_MAP}
        self._skip_keywords = SHARED_SKIP_KEYWORDS | self.EXTRA_SKIP_KEYWORDS

    @property
    def listing_url(self) -> str:
        return f"{self.BASE_URL}/Facilities"

    def _should_skip(self, name: str) -> bool:
        """Check if a facility name indicates a non-park entry."""
        name_lower = name.lower()
        if any(kw in name_lower for kw in self._skip_keywords):
            if "park" not in name_lower:
                return True
        return False

    def _get_driver(self):
        """Create an undetected Chrome driver."""
        import undetected_chromedriver as uc
        options = uc.ChromeOptions()
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-extensions")
        driver = uc.Chrome(options=options, version_main=146)
        return driver

    def _get_listing_urls(self) -> list[str]:
        """Use Selenium to load all facility URLs from the paginated listing."""
        driver = self._get_driver()
        try:
            driver.get(self.listing_url)
            time.sleep(3)

            # Change page size to 100 to show all facilities on one page
            driver.execute_script("""
                var sel = document.getElementById('facilityListingPagingDropDown');
                if (sel) { sel.value = '100'; sel.dispatchEvent(new Event('change')); }
            """)
            time.sleep(2)

            # Trigger search to reload with new page size
            driver.execute_script("SearchSidebar.searchByPage(1);")
            time.sleep(5)

            html = driver.page_source
        finally:
            try:
                driver.quit()
            except OSError:
                pass

        soup = BeautifulSoup(html, "html.parser")
        seen = set()
        urls = []

        for link in soup.select('a[href*="/Facilities/Facility/Details/"]'):
            href = link.get("href", "")
            full = f"{self.BASE_URL}{href}" if href.startswith("/") else href
            full = full.split("?")[0]
            if full not in seen:
                seen.add(full)
                name = link.get_text(strip=True)
                if name and self._should_skip(name):
                    logger.debug("Skipping non-park facility from listing: %s", name)
                    continue
                urls.append(full)

        logger.info("Selenium: found %d facility URLs (after filtering)", len(urls))
        return urls

    def _address_cities(self) -> list[str]:
        """Return city names to match in addresses. Override for multi-city counties."""
        return [self.CITY]

    def _parse_address(self, text: str) -> str | None:
        """Extract a street address from the detail page text."""
        cities = "|".join(re.escape(c) for c in self._address_cities())
        pattern = (
            r"(\d+\s+[A-Za-z0-9 .]+(?:St|Street|Ave|Avenue|Rd|Road|Dr|Drive|"
            r"Blvd|Boulevard|Way|Ln|Lane|Ct|Court|Pl|Place|Pkwy|Parkway|"
            r"Circle|Loop|Trail|Park|Highway|Hwy)[.\s]*)"
            rf"[,\s]*({cities}),?\s*NC\s*(\d{{5}})"
        )
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            street = m.group(1).strip().rstrip(".")
            city = m.group(2)
            zipcode = m.group(3)
            return f"{street}, {city}, NC {zipcode}"
        return None

    def _parse_detail_page(self, html: str, url: str) -> dict | None:
        """Parse a single CivicPlus facility detail page."""
        soup = BeautifulSoup(html, "html.parser")

        # Name — in h2 or h4 tag
        name = None
        for tag in ["h2", "h4"]:
            heading = soup.find(tag)
            if heading:
                text = heading.get_text(strip=True)
                if text and "Facilities" not in text and "Rating" not in text:
                    name = text
                    break

        if not name:
            return None

        # Extract ID from URL
        id_match = re.search(r"-(\d+)$", url.rstrip("/"))
        source_id = id_match.group(1) if id_match else name

        # Check if this is actually a park
        if self._should_skip(name):
            logger.debug("Skipping non-park facility: %s", name)
            return None

        body_text = soup.get_text("\n", strip=True)

        # Address
        address = self._parse_address(body_text)

        # Phone
        phone = None
        phone_link = soup.find("a", href=re.compile(r"^tel:"))
        if phone_link:
            phone = phone_link.get_text(strip=True)

        # Features — in the "Features" section, typically as bullet list
        amenities = {}
        features_heading = soup.find(string=re.compile(r"^\s*Features\s*$"))
        if features_heading:
            parent = features_heading.find_parent()
            if parent:
                ul = parent.find_next("ul")
                if ul:
                    for li in ul.find_all("li"):
                        text = li.get_text(strip=True)
                        if text:
                            key = self._feature_map.get(text.lower())
                            if key:
                                amenities[key] = True
                            else:
                                logger.debug("Unmapped feature: %r", text)

        # Fallback: parse bullet text from sibling elements
        if not amenities and features_heading:
            parent = features_heading.find_parent()
            if parent:
                sibling = parent.find_next_sibling()
                if sibling:
                    for line in sibling.get_text("\n").split("\n"):
                        line = line.strip().lstrip("•·▪-").strip()
                        if line:
                            key = self._feature_map.get(line.lower())
                            if key:
                                amenities[key] = True

        # Size (acres)
        size_acres = None
        size_match = re.search(r"(?:is|approximately)\s+([\d.]+)\s*acres?", body_text, re.IGNORECASE)
        if size_match:
            size_acres = float(size_match.group(1))

        return {
            "source": self.SOURCE_NAME,
            "source_id": str(source_id),
            "name": name,
            "latitude": None,
            "longitude": None,
            "address": address,
            "city": self.CITY,
            "county": self.COUNTY,
            "phone": phone,
            "url": url,
            "amenities": amenities,
            "extras": {
                "size_acres": size_acres,
            },
        }

    def fetch(self) -> list[dict]:
        """Fetch all parks — Selenium listing + requests detail pages."""
        detail_urls = self._get_listing_urls()
        logger.info("Found %d facility detail URLs", len(detail_urls))

        session = requests.Session()
        session.headers.update(HEADERS)

        parks = []
        for i, url in enumerate(detail_urls):
            logger.info("Fetching detail %d/%d: %s", i + 1, len(detail_urls), url)
            try:
                resp = session.get(url, timeout=30)
                resp.raise_for_status()
                park = self._parse_detail_page(resp.text, url)
                if park:
                    parks.append(park)
            except Exception:
                logger.warning("Failed to fetch %s", url, exc_info=True)

            if i < len(detail_urls) - 1:
                time.sleep(REQUEST_DELAY)

        logger.info("%s: fetched %d parks from %d facility pages",
                    self.SOURCE_NAME, len(parks), len(detail_urls))
        return parks
