"""Wilmington parks scraper.

Source: https://www.wilmingtonnc.gov/files/assets/city/v/1/parks-amp-rec/documents/amenities/parksamenitiessheet_2025-3.pdf

The city publishes a PDF amenities spreadsheet.  We use Selenium to bypass
the WAF (403), download the PDF content, and parse with pdfplumber.
"""

from __future__ import annotations

import io
import logging
import re
import time

logger = logging.getLogger(__name__)

_PDF_URL = (
    "https://www.wilmingtonnc.gov/files/assets/city/v/1/"
    "parks-amp-rec/documents/amenities/parksamenitiessheet_2025-3.pdf"
)


def _get_driver():
    import undetected_chromedriver as uc
    options = uc.ChromeOptions()
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-extensions")
    return uc.Chrome(options=options, version_main=146)


def _download_pdf_via_selenium() -> bytes:
    """Use Selenium to bypass WAF and download the PDF bytes."""
    import base64
    driver = _get_driver()
    try:
        # Visit the main site first to establish cookies/session
        driver.get("https://www.wilmingtonnc.gov/")
        time.sleep(2)
        # Use JS fetch() inside the browser session to download the PDF
        b64 = driver.execute_async_script("""
            const [url, callback] = [arguments[0], arguments[arguments.length - 1]];
            fetch(url).then(r => r.arrayBuffer()).then(buf => {
                const bytes = new Uint8Array(buf);
                let binary = '';
                for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
                callback(btoa(binary));
            }).catch(e => callback('ERROR:' + e.message));
        """, _PDF_URL)
        if isinstance(b64, str) and b64.startswith("ERROR:"):
            raise RuntimeError(f"JS fetch failed: {b64}")
        return base64.b64decode(b64)
    finally:
        try:
            driver.quit()
        except OSError:
            pass


_STREET_RE = re.compile(
    r"(Street|St|Drive|Dr|Avenue|Ave|Road|Rd|Boulevard|Blvd|Circle|Cir|"
    r"Lane|Ln|Court|Ct|Place|Pl|Parkway|Way|Trail)",
    re.I,
)


def _parse_pdf_text(pdf) -> list[dict]:
    """Extract park names and addresses from the PDF text.

    The PDF is a landscape amenities spreadsheet. Park names and addresses
    appear in the leftmost area. We extract text lines, classify them
    (name / address / acreage / junk), then pair names with addresses.
    """
    parks: list[dict] = []
    seen: set[str] = set()

    _SKIP = {
        "skrap", "seitilicaf", "parks & amenities", "parks",
        "reserve reserve", "contact a staff member today!",
    }

    for page in pdf.pages:
        text = page.extract_text()
        if not text:
            continue

        lines = [l.strip() for l in text.split("\n") if l.strip()]

        current_name: str | None = None
        for line in lines:
            low = line.lower()

            # Skip reversed column headers and meta
            if low in _SKIP:
                continue
            # Reversed headers always start with lowercase or ')'
            if line[0].islower() or line[0] == ")":
                continue
            if "city of wilmington" in low or "updated" in low:
                continue
            if "shelters at" in low or "available for" in low:
                continue
            if "info@" in low or "the fragrance" in low:
                continue
            if low.startswith("downtown "):
                continue

            # Pure number → acreage or "N/A" → skip
            if re.match(r"^[\d.]+$", line):
                continue
            if line == "N/A":
                continue

            # Address line: starts with digit + space + more text,
            # or compass direction like "N. Water Street"
            is_address = bool(re.match(r"^\d+\s+\S", line))
            if not is_address:
                is_address = bool(re.match(r"^[NESW]\.?\s+\w", line) and _STREET_RE.search(line))

            if is_address:
                if current_name:
                    # Strip trailing acreage from name
                    clean_name = re.sub(r"\s+[\d.]+$", "", current_name).strip()
                    if clean_name and clean_name not in seen:
                        seen.add(clean_name)
                        sid = re.sub(r"[^a-z0-9]+", "_", clean_name.lower()).strip("_")
                        parks.append({
                            "source": "wilmington",
                            "source_id": f"wilmington_{sid}",
                            "name": clean_name,
                            "latitude": None,
                            "longitude": None,
                            "address": f"{line}, Wilmington, NC",
                            "city": "Wilmington",
                            "county": "New Hanover County",
                            "phone": None,
                            "url": _PDF_URL,
                            "amenities": {},
                            "extras": {},
                        })
                    current_name = None
            else:
                # Treat as a potential park name
                if current_name and current_name not in seen:
                    # Previous name had no address
                    clean_name = re.sub(r"\s+[\d.]+$", "", current_name).strip()
                    if clean_name:
                        seen.add(clean_name)
                        sid = re.sub(r"[^a-z0-9]+", "_", clean_name.lower()).strip("_")
                        parks.append({
                            "source": "wilmington",
                            "source_id": f"wilmington_{sid}",
                            "name": clean_name,
                            "latitude": None,
                            "longitude": None,
                            "address": None,
                            "city": "Wilmington",
                            "county": "New Hanover County",
                            "phone": None,
                            "url": _PDF_URL,
                            "amenities": {},
                            "extras": {},
                        })
                current_name = line

    return parks


def fetch() -> list[dict]:
    import pdfplumber

    logger.info("wilmington: downloading PDF from %s", _PDF_URL)
    pdf_content = _download_pdf_via_selenium()

    with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
        parks = _parse_pdf_text(pdf)

    logger.info("wilmington: parsed %d parks from PDF", len(parks))
    return parks


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(message)s")
    parks = fetch()
    print(f"\n{'='*60}")
    print(f"Fetched {len(parks)} Wilmington parks")
    for p in parks:
        addr = p.get("address") or "N/A"
        print(f"  {p['name']:40s} | {addr}")
