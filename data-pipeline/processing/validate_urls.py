"""Validate and fix park URLs.

Checks every park URL for reachability (HEAD request with GET fallback),
applies hard-coded overrides for known-bad URLs, and flags unreachable
URLs.  Override URLs are also validated so stale overrides get caught.

Usage in pipeline:
    from processing.validate_urls import validate_urls
    parks = validate_urls(parks)
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

logger = logging.getLogger(__name__)

# ---- Hard-coded URL overrides --------------------------------------------
# Key: park name (exact match, case-insensitive)
# Value: correct URL
#
# Add entries here when a source provides a known-bad URL.
# These are validated too — if an override goes stale, it will be logged.

URL_OVERRIDES: dict[str, str] = {
    "Lake Benson Park": "https://www.garnernc.gov/departments/parks-recreation-and-cultural-resources/garner-parks/lake-benson-park",
}

# Timeout for each URL check (seconds)
_TIMEOUT = 10

# Max parallel requests
_MAX_WORKERS = 10

# HTTP status codes we consider "valid" (page exists)
_OK_STATUSES = range(200, 400)

# Trusted URL domains — URLs from these domains won't be cleared even if
# validation fails (the sites are known to block bot-like requests).
_TRUSTED_DOMAINS = {
    "johnstonnc.gov",
    "garnernc.gov",
    "alamancecountync.gov",
}

# Set of override URLs — these are trusted (manually verified) and
# won't be cleared even if validation fails (some sites block bots).
_OVERRIDE_URLS = set(URL_OVERRIDES.values())


def _is_trusted_url(url: str) -> bool:
    """Check if a URL belongs to a trusted domain."""
    from urllib.parse import urlparse
    hostname = urlparse(url).hostname or ""
    return any(hostname == d or hostname.endswith("." + d) for d in _TRUSTED_DOMAINS)


def _check_url(url: str) -> tuple[bool, int | None]:
    """Check if a URL is reachable. Returns (ok, status_code).

    Tries HEAD first (lightweight), falls back to GET if HEAD returns
    405 or an error.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    }
    try:
        resp = requests.head(url, timeout=_TIMEOUT, headers=headers, allow_redirects=True)
        if resp.status_code == 405:
            # Some servers don't allow HEAD — try GET
            resp = requests.get(url, timeout=_TIMEOUT, headers=headers, allow_redirects=True, stream=True)
            resp.close()
        return resp.status_code in _OK_STATUSES, resp.status_code
    except requests.RequestException as e:
        logger.debug("URL unreachable: %s — %s", url, e)
        return False, None


def validate_urls(parks: list[dict], max_workers: int = _MAX_WORKERS) -> list[dict]:
    """Validate and fix URLs for all parks.

    Steps:
    1. Apply hard-coded overrides (by park name)
    2. Validate all URLs in parallel
    3. For parks with failing URLs, clear the URL and log a warning

    Parameters
    ----------
    parks:
        List of park dicts (must have ``name`` and optionally ``url``).
    max_workers:
        Max parallel HTTP requests for validation.

    Returns
    -------
    list[dict]
        Same parks with URLs fixed or cleared.
    """
    overrides_lower = {k.lower(): v for k, v in URL_OVERRIDES.items()}

    # Step 1: Apply overrides
    override_count = 0
    for park in parks:
        key = park["name"].lower()
        if key in overrides_lower:
            old_url = park.get("url")
            new_url = overrides_lower[key]
            if old_url != new_url:
                logger.info("Override URL for %s: %s → %s", park["name"], old_url, new_url)
                override_count += 1
            park["url"] = new_url

    if override_count:
        logger.info("Applied %d URL overrides", override_count)

    # Step 2: Collect unique URLs to validate
    url_to_parks: dict[str, list[dict]] = {}
    for park in parks:
        url = park.get("url")
        if url:
            url_to_parks.setdefault(url, []).append(park)

    if not url_to_parks:
        logger.info("No URLs to validate")
        return parks

    logger.info("Validating %d unique URLs across %d parks…",
                len(url_to_parks), sum(len(v) for v in url_to_parks.values()))

    # Step 3: Validate in parallel
    results: dict[str, tuple[bool, int | None]] = {}

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_to_url = {pool.submit(_check_url, url): url for url in url_to_parks}

        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                ok, status = future.result()
                results[url] = (ok, status)
            except Exception:
                results[url] = (False, None)
                logger.exception("Error checking %s", url)

    # Step 4: Report results and clear bad URLs
    valid_count = 0
    invalid_count = 0

    for url, (ok, status) in sorted(results.items(), key=lambda x: x[0]):
        park_names = [p["name"] for p in url_to_parks[url]]
        if ok:
            valid_count += 1
        else:
            invalid_count += 1
            status_str = str(status) if status else "unreachable"
            is_trusted = url in _OVERRIDE_URLS or _is_trusted_url(url)
            if is_trusted:
                logger.warning("BAD URL (trusted, keeping) [%s]: %s — used by: %s",
                               status_str, url, ", ".join(park_names))
            else:
                logger.warning("BAD URL [%s]: %s — used by: %s",
                               status_str, url, ", ".join(park_names))
                # Clear the URL so the frontend doesn't link to a dead page
                for park in url_to_parks[url]:
                    park["url"] = None
                    park.setdefault("_validation_notes", []).append(
                        f"URL removed ({status_str}): {url}"
                    )

    logger.info("URL validation: %d valid, %d invalid (cleared)", valid_count, invalid_count)
    return parks
