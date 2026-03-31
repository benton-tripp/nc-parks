"""Johnston County parks scraper.

Source: https://www.johnstonnc.gov/parks/PlaygroundParks.cfm

The listing page has a Leaflet map with L.marker() calls containing lat/lon,
and links to detail pages (pcontent.cfm?id=N) with amenities, addresses,
descriptions, photos, and accessibility info.

Strategy:
  1. Fetch listing page → extract markers (lat, lon, name) + detail URLs
  2. Fetch each detail page → extract amenities, address, description, hours, etc.
  3. Return normalized park dicts matching the pipeline schema
"""

from __future__ import annotations

import logging
import re
import time

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

LISTING_URL = "https://www.johnstonnc.gov/parks/PlaygroundParks.cfm"

# Delay between detail page requests to be polite
REQUEST_DELAY = 0.5  # seconds

# Map scraped amenity text → normalized amenity keys
AMENITY_MAP = {
    "baseball":          "ball_fields",
    "basketball":        "basketball_courts",
    "bocce":             "bocce",
    "bmx":               "bmx_track",
    "camping":           "camping",
    "canoe":             "canoe_kayak",
    "concessions":       "concessions",
    "disc golf":         "disc_golf",
    "dog park":          "dog_park",
    "equestrian":        "equestrian",
    "fishing":           "fishing",
    "football":          "multipurpose_field",
    "gardens":           "gardens",
    "hiking trails":     "walking_trails",
    "horseshoe":         "horseshoe",
    "kayak":             "canoe_kayak",
    "lacrosse":          "multipurpose_field",
    "multipurpose":      "multipurpose_field",
    "nature trails":     "walking_trails",
    "open space":        "open_space",
    "pickleball":        "pickleball",
    "picnic shelters":   "picnic_shelter",
    "picnic":            "picnic_shelter",
    "playground":        "playground",
    "pool":              "swimming_pool",
    "restrooms":         "restrooms",
    "shelter":           "picnic_shelter",
    "skate park":        "skate_park",
    "soccer":            "multipurpose_field",
    "softball":          "ball_fields",
    "splash pad":        "splash_pad",
    "swimming":          "swimming_pool",
    "t-ball":            "ball_fields",
    "tennis":            "tennis_courts",
    "track":             "track",
    "trails":            "walking_trails",
    "volleyball":        "sand_volleyball",
    "walking trails":    "walking_trails",
    "walking":           "walking_trails",
}


def _get(url: str) -> requests.Response:
    """GET with retries and a browser-like User-Agent."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        )
    }
    for attempt in range(3):
        try:
            resp = requests.get(url, headers=headers, timeout=20)
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            if attempt == 2:
                raise
            logger.warning("Retry %d for %s: %s", attempt + 1, url, exc)
            time.sleep(2)


def _extract_markers(html: str) -> list[dict]:
    """Extract L.marker() calls from the listing page JavaScript."""
    # Pattern: L.marker([lat, lon]).bindPopup("<b>Name</b>...")
    # The HTML may have &lt;b&gt; or <b> depending on escaping
    patterns = [
        r'L\.marker\(\[([0-9.\-]+),\s*([0-9.\-]+)\]\)\.bindPopup\("<b>(.+?)</b>',
        r'L\.marker\(\[([0-9.\-]+),\s*([0-9.\-]+)\]\)\.bindPopup\("&lt;b&gt;(.+?)&lt;/b&gt;',
        r"L\.marker\(\[([0-9.\-]+),\s*([0-9.\-]+)\]\)\.bindPopup\('<b>(.+?)</b>",
    ]
    for pattern in patterns:
        matches = re.findall(pattern, html)
        if matches:
            return [
                {"lat": float(lat), "lon": float(lon), "name": name.strip()}
                for lat, lon, name in matches
            ]
    return []


def _extract_detail_links(html: str) -> dict[str, str]:
    """Extract park name → detail URL mapping from listing page links."""
    soup = BeautifulSoup(html, "html.parser")
    links = {}
    for a in soup.find_all("a", href=re.compile(r"pcontent\.cfm\?id=\d+")):
        name = a.get_text(strip=True)
        href = a["href"]
        if not href.startswith("http"):
            href = "https://www.johnstonnc.gov/parks/" + href
        if name:
            links[name] = href
    return links


def _normalize_amenity(text: str) -> str | None:
    """Map a scraped amenity string to a normalized key."""
    lower = text.strip().lower()
    # Direct match
    if lower in AMENITY_MAP:
        return AMENITY_MAP[lower]
    # Substring match (e.g., "Hiking Trails" matches "hiking trails")
    for keyword, key in AMENITY_MAP.items():
        if keyword in lower or lower in keyword:
            return key
    return None


def _scrape_detail(url: str) -> dict:
    """Scrape a single park detail page for amenities, address, etc."""
    resp = _get(url)
    soup = BeautifulSoup(resp.text, "html.parser")
    info = {
        "description": None,
        "amenities_raw": [],
        "address": None,
        "city": None,
        "state": None,
        "zip_code": None,
        "url": None,
        "hours": None,
        "accessible": None,
        "photos": [],
    }

    # --- Description: first <p> in the main content area ---
    # The detail page structure: <h1>Name</h1> then description <p>,
    # then images, then ## Amenities, ## Contact, etc.
    main = soup.find("main") or soup.find("div", class_="content") or soup
    first_p = main.find("p")
    if first_p:
        desc = first_p.get_text(strip=True)
        if desc and len(desc) > 10:
            info["description"] = desc

    # --- Amenities section ---
    amenity_heading = soup.find(
        lambda tag: tag.name in ("h2", "h3", "h4", "strong")
        and "amenities" in tag.get_text(strip=True).lower()
    )
    if amenity_heading:
        # Amenities are in spans/divs after the heading, or in a list
        container = amenity_heading.find_next_sibling()
        if container:
            # Try list items first
            items = container.find_all("li")
            if items:
                info["amenities_raw"] = [li.get_text(strip=True) for li in items]
            else:
                # May be individual span/div elements or just text
                spans = container.find_all(["span", "div", "p"])
                if spans:
                    info["amenities_raw"] = [s.get_text(strip=True) for s in spans if s.get_text(strip=True)]
                else:
                    # Plain text — split by common delimiters
                    text = container.get_text(strip=True)
                    if text:
                        # These are often concatenated with no separator;
                        # try splitting on capital letters
                        parts = re.findall(r'[A-Z][a-z\-/ ]+(?:\s+[A-Z][a-z\-/ ]+)*', text)
                        if parts:
                            info["amenities_raw"] = [p.strip() for p in parts if p.strip()]
                        else:
                            info["amenities_raw"] = [text]

    # --- Contact section (address, URL, hours) ---
    contact_heading = soup.find(
        lambda tag: tag.name in ("h2", "h3", "h4", "strong")
        and "contact" in tag.get_text(strip=True).lower()
    )
    if contact_heading:
        contact_div = contact_heading.find_next_sibling()
        if contact_div:
            contact_text = contact_div.get_text("\n", strip=True)
            lines = [l.strip() for l in contact_text.split("\n") if l.strip()]

            # Look for address pattern: street, city, state zip
            for i, line in enumerate(lines):
                nc_match = re.search(r'(.+),\s*NC\s+(\d{5})', line)
                if nc_match:
                    info["city"] = nc_match.group(1).strip()
                    info["zip_code"] = nc_match.group(2)
                    info["state"] = "NC"
                    # Previous line is the street address if it exists
                    # and isn't the park name
                    if i > 0 and not lines[i - 1].startswith("http"):
                        # Check the line above might be street address
                        street = lines[i - 1] if re.search(r'\d', lines[i - 1]) else None
                        if street:
                            info["address"] = f"{street}, {line}"
                        else:
                            info["address"] = line
                    break

            # External URL
            link = contact_div.find("a", href=re.compile(r"^https?://"))
            if link and "johnstonnc.gov" not in link["href"]:
                info["url"] = link["href"]

            # Hours
            hours_match = re.search(r'Hours?:\s*(.+)', contact_text, re.IGNORECASE)
            if hours_match:
                info["hours"] = hours_match.group(1).strip()

    # --- Accessibility ---
    access_heading = soup.find(
        lambda tag: tag.name in ("h2", "h3", "h4", "strong")
        and "accessibility" in tag.get_text(strip=True).lower()
    )
    if access_heading:
        access_div = access_heading.find_next_sibling()
        if access_div:
            text = access_div.get_text(strip=True).lower()
            info["accessible"] = "yes" in text

    # --- Photos ---
    for img in main.find_all("img"):
        src = img.get("src", "")
        if "imgParks/" in src:
            if not src.startswith("http"):
                src = "https://www.johnstonnc.gov" + src
            info["photos"].append({
                "url": src,
                "alt": img.get("alt", ""),
            })

    return info


def fetch() -> list[dict]:
    """Fetch all Johnston County parks from the county website.

    Returns a list of park dicts in the pipeline's raw schema.
    """
    logger.info("Fetching Johnston County listing page...")
    resp = _get(LISTING_URL)
    html = resp.text

    markers = _extract_markers(html)
    detail_links = _extract_detail_links(html)

    if not markers:
        logger.error("No map markers found on listing page")
        return []

    logger.info("Found %d markers and %d detail links", len(markers), len(detail_links))

    # Match markers to detail links by name
    parks = []
    for marker in markers:
        name = marker["name"]
        detail_url = detail_links.get(name)

        park = {
            "source": "johnston_county",
            "source_id": f"johnston_{name.lower().replace(' ', '_').replace(',', '')}",
            "name": name,
            "latitude": marker["lat"],
            "longitude": marker["lon"],
            "county": "Johnston",
            "state": "NC",
            "amenities": {},
            "address": None,
            "url": None,
            "phone": None,
            "description": None,
            "hours": None,
            "accessible": None,
            "photos": [],
        }

        # Scrape detail page if we have a link
        if detail_url:
            logger.info("  Scraping detail page: %s", name)
            try:
                detail = _scrape_detail(detail_url)

                # Map raw amenity strings to normalized keys
                amenities = {}
                for raw in detail["amenities_raw"]:
                    key = _normalize_amenity(raw)
                    if key:
                        amenities[key] = True
                    else:
                        logger.debug("Unmapped amenity %r at %s", raw, name)
                park["amenities"] = amenities

                park["address"] = detail["address"]
                park["description"] = detail["description"]
                park["hours"] = detail["hours"]
                park["accessible"] = detail["accessible"]
                park["photos"] = detail["photos"]

                # Prefer external URL from detail page, fall back to detail page itself
                if detail["url"]:
                    park["url"] = detail["url"]
                else:
                    park["url"] = detail_url

                time.sleep(REQUEST_DELAY)

            except Exception as exc:
                logger.warning("Failed to scrape detail for %s: %s", name, exc)
        else:
            logger.debug("No detail link found for marker: %s", name)

        parks.append(park)

    logger.info("Johnston County: %d parks fetched", len(parks))
    return parks


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    results = fetch()
    print(f"\nTotal: {len(results)} parks")
    for p in results:
        amenity_count = sum(1 for v in p["amenities"].values() if v)
        photo_count = len(p.get("photos", []))
        print(f"  {p['name']}")
        print(f"    {p['latitude']:.4f}, {p['longitude']:.4f}")
        print(f"    Amenities: {amenity_count}  Photos: {photo_count}")
        if p["address"]:
            print(f"    Address: {p['address']}")
        if p["url"]:
            print(f"    URL: {p['url']}")
        print()