"""New Hanover County parks scraper.

Source: https://www.nhcgov.com/DocumentCenter/View/844/Parks-Guide-PDF?bidId=

The county publishes a Parks Guide PDF.  We download it and use pdfplumber to
extract park data dynamically.  No hard-coded fallback.
"""

from __future__ import annotations

import io
import logging
import re

import requests

logger = logging.getLogger(__name__)

_PDF_URL = "https://www.nhcgov.com/DocumentCenter/View/844/Parks-Guide-PDF?bidId="
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
}

# Patterns for park entries in the PDF text
_PARK_NAME_RE = re.compile(
    r"([A-Z][A-Za-z\s.'-]+(?:Park|Center|Preserve|Trail|Complex|Field|Landing|Hollow))"
)
_ADDRESS_RE = re.compile(
    r"(\d+\s+[A-Za-z0-9\s.]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|"
    r"Boulevard|Blvd|Way|Circle|Cir|Court|Ct|Place|Pl|Parkway|Pkwy|SE|NE|SW|NW))"
    r"(?:[,\s]*(?:Wilmington|Castle Hayne|Wrightsville|Leland|Ogden))?"
    r"(?:[,\s]*NC)?(?:[,\s]*\d{5})?",
    re.IGNORECASE,
)


def fetch() -> list[dict]:
    import pdfplumber

    logger.info("new_hanover_county: downloading PDF from %s", _PDF_URL)
    resp = requests.get(_PDF_URL, headers=_HEADERS, timeout=60)
    resp.raise_for_status()

    parks: list[dict] = []
    seen: set[str] = set()

    with pdfplumber.open(io.BytesIO(resp.content)) as pdf:
        for page in pdf.pages:
            table = page.extract_table()
            if not table:
                continue

            for row in table:
                if not row or not row[0]:
                    continue

                cell0 = str(row[0]).strip()
                if not cell0:
                    continue

                # Column 0 = "ParkName\nAddress" or "ParkName\nNamePart2\nAddress"
                parts = [p.strip() for p in cell0.split("\n") if p.strip()]
                if not parts:
                    continue

                # Find where the address starts (line beginning with digit)
                name_parts: list[str] = []
                address = None
                for part in parts:
                    if address is None and not re.match(r"^\d+\s+", part):
                        name_parts.append(part)
                    else:
                        if address is None:
                            address = part
                        # ignore extra lines after address

                name = " ".join(name_parts).strip()
                # Fix PDF extraction artifacts (e.g., "Greenfi eld" -> "Greenfield")
                name = re.sub(r"([a-z]) ([a-z])", r"\1\2", name)

                # Skip header row (reversed text)
                if name.lower() in ("park", "park name", "") or name[0].islower():
                    continue
                if name in seen:
                    continue
                seen.add(name)

                # Column 1 = acreage
                acreage = None
                if len(row) > 1 and row[1]:
                    acreage = str(row[1]).strip().replace("\n", " ")

                # Append city/state to address if present
                addr_full = f"{address}, New Hanover County, NC" if address else None

                source_id = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
                extras = {}
                if acreage:
                    extras["acreage"] = acreage

                parks.append({
                    "source": "new_hanover_county",
                    "source_id": f"new_hanover_county_{source_id}",
                    "name": name,
                    "latitude": None,
                    "longitude": None,
                    "address": addr_full,
                    "city": None,
                    "county": "New Hanover County",
                    "phone": None,
                    "url": _PDF_URL,
                    "amenities": {},
                    "extras": extras,
                })

    logger.info("new_hanover_county: parsed %d parks from PDF", len(parks))
    return parks


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(message)s")
    parks = fetch()
    print(f"\n{'='*60}")
    print(f"Fetched {len(parks)} New Hanover County parks")
    for p in parks:
        addr = p.get("address") or "N/A"
        print(f"  {p['name']:35s} | {addr}")
