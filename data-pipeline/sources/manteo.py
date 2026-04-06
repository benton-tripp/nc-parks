"""Manteo parks scraper.

Source: https://www.manteonc.gov/community/visitors/parks-and-playgrounds

Granicus CMS with all parks on a single page.  Parks described in prose blocks
with headings (h2/h3/h4/strong).  Uses Selenium to render the JS-heavy
Granicus page, then parses park names and addresses from the content.
"""

from __future__ import annotations

import logging
import re
import time

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_URL = "https://www.manteonc.gov/community/visitors/parks-and-playgrounds"
PAGE_DELAY = 4

_ADDRESS_RE = re.compile(
    r"(\d+\s+[A-Za-z0-9\s.]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|"
    r"Boulevard|Blvd|Way|Circle|Cir|Court|Ct|Place|Pl|Parkway|Pkwy))"
    r"(?:[,\s]*Manteo)?(?:[,\s]*NC)?(?:[,\s]*\d{5})?",
    re.IGNORECASE,
)

_AMENITY_KEYWORDS: dict[str, str] = {
    "playground": "playground",
    "swing": "swings",
    "slide": "slides",
    "picnic": "picnic_shelter",
    "pavilion": "pavilion",
    "shelter": "picnic_shelter",
    "restroom": "restrooms",
    "bathroom": "restrooms",
    "skate": "skate_park",
    "basketball": "basketball_courts",
    "tennis": "tennis_courts",
    "trail": "walking_trails",
    "fishing": "fishing",
    "boat": "boat_ramp",
    "kayak": "kayak_launch",
    "grill": "grills",
}


def _get_driver():
    import undetected_chromedriver as uc
    options = uc.ChromeOptions()
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-extensions")
    return uc.Chrome(options=options, version_main=146)


def _extract_amenities(text: str) -> dict[str, bool]:
    amenities: dict[str, bool] = {}
    lower = text.lower()
    for keyword, key in _AMENITY_KEYWORDS.items():
        if keyword in lower:
            amenities[key] = True
    return amenities


def fetch() -> list[dict]:
    driver = _get_driver()
    try:
        logger.info("manteo: fetching %s", _URL)
        driver.get(_URL)
        time.sleep(PAGE_DELAY)

        soup = BeautifulSoup(driver.page_source, "html.parser")
    finally:
        try:
            driver.quit()
        except OSError:
            pass

    # Find the main content area
    content = soup.select_one(".content_area") or soup.select_one(".normal_content_area") or soup

    parks: list[dict] = []
    seen_names: set[str] = set()

    # The Manteo parks page uses a mix of headings (h2, h3) and plain <p> tags
    # for park names.  Each park name is followed by description paragraphs.
    # We iterate all direct children and detect park-name paragraphs by:
    # - headings (h2/h3/h4) or
    # - short <p> tags whose text looks like a proper name (title case, < 60 chars, no period)
    children = list(content.children)
    i = 0
    while i < len(children):
        child = children[i]
        if not hasattr(child, "name") or not child.name:
            i += 1
            continue

        text = child.get_text(strip=True)
        if not text:
            i += 1
            continue

        is_heading = child.name in ["h2", "h3", "h4"]
        is_name_paragraph = (
            child.name == "p"
            and 3 < len(text) < 60
            and "." not in text[:30]  # Names don't have periods early
            and not text[0].isdigit()  # Not an address
            and text[0].isupper()  # Starts with capital
        )

        if not is_heading and not is_name_paragraph:
            i += 1
            continue

        name = re.sub(r"\s+", " ", text).strip()

        # Skip navigation/footer items
        _skip = {"popular searches", "jump to subpage", "resources", "events",
                 "visit", "connect", "come & visit", "connect with us",
                 "parks and playgrounds", "parks & playgrounds", "contact",
                 "location & hours", "empty heading", "print", "feedback"}
        if name.lower() in _skip:
            i += 1
            continue

        if name in seen_names:
            i += 1
            continue

        # Gather description text from following siblings until next park name
        desc_parts: list[str] = []
        j = i + 1
        while j < len(children):
            sib = children[j]
            if not hasattr(sib, "name") or not sib.name:
                j += 1
                continue
            sib_text = sib.get_text(strip=True)
            if not sib_text:
                j += 1
                continue
            # Stop if we hit another heading or short name-like paragraph
            if sib.name in ["h2", "h3", "h4"]:
                break
            if (sib.name == "p" and 3 < len(sib_text) < 60
                    and "." not in sib_text[:30]
                    and not sib_text[0].isdigit()
                    and sib_text[0].isupper()
                    and not any(w in sib_text.lower() for w in ["located", "built", "dedicated", "order to", "the ", "in "])):
                break
            desc_parts.append(sib_text)
            j += 1

        description = " ".join(desc_parts)

        # Extract address
        address = None
        addr_match = _ADDRESS_RE.search(description)
        if addr_match:
            address = addr_match.group(0).strip()
            if not re.search(r"Manteo", address, re.I):
                address += ", Manteo, NC 27954"

        amenities = _extract_amenities(name + " " + description)

        seen_names.add(name)
        source_id = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
        parks.append({
            "source": "manteo",
            "source_id": f"manteo_{source_id}",
            "name": name,
            "latitude": None,
            "longitude": None,
            "address": address,
            "city": "Manteo",
            "county": "Dare County",
            "phone": None,
            "url": _URL,
            "amenities": amenities,
            "extras": {},
        })

    logger.info("manteo: fetched %d parks", len(parks))
    return parks


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(message)s")
    parks = fetch()
    print(f"\n{'='*60}")
    print(f"Fetched {len(parks)} Manteo parks")
    for p in parks:
        amenity_list = sorted(k for k, v in p.get("amenities", {}).items() if v)
        addr = p.get("address") or "N/A"
        print(f"  {p['name']:40s} | {addr:50s} | {amenity_list}")
