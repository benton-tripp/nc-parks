"""NC Parks data pipeline orchestrator.

Coordinates the full ETL flow:
  1. Fetch     — pull raw data from each source
  2. Normalize — map into canonical park schema
  3. Geocode   — forward (address→coords) + reverse (coords→address)
  4. Enrich    — add county via point-in-polygon, add geohash
  5. Validate  — check/fix park URLs, apply overrides
  6. Deduplicate — merge near-identical parks across sources
  7. Save      — write JSON artifacts to data/

Usage:
    python -m data-pipeline.pipeline                      # all sources
    python -m data-pipeline.pipeline --source wake_county # single source
    python -m data-pipeline.pipeline --dry-run             # fetch only, no save
    python -m data-pipeline.pipeline --refresh-boundaries  # re-fetch county polys
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

# Resolve paths relative to this file so it works from any cwd
_ROOT = Path(__file__).resolve().parent
_DATA = _ROOT.parent / "data"
_RAW = _DATA / "raw"
_PROCESSED = _DATA / "processed"
_FINAL = _DATA / "final"
_REFERENCE = _DATA / "reference"

# Add the pipeline directory to sys.path so we can import sources/processing
# even though the directory name has a hyphen (not a valid Python identifier).
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

logger = logging.getLogger(__name__)

# ---- Source registry -----------------------------------------------------
# Each entry: name → module path's fetch() callable
# We import lazily so missing sources don't block the ones that work.

SOURCES = {
    "wake_county":      "sources.wake_county",
    "johnston_county":  "sources.johnston_county",
    "osm":              "sources.osm",
    "alamance_county":  "sources.alamance_county",
    "greensboro":       "sources.greensboro",
    "high_point":       "sources.high_point",
    "playground_explorers": "sources.playground_explorers",
    "southern_pines":   "sources.southern_pines",
    "nash_county":      "sources.nash_county",
    "kill_devil_hills": "sources.kill_devil_hills",
    "graham":           "sources.graham",
    "manteo":           "sources.manteo",
    "elizabeth_city":   "sources.elizabeth_city",
    "new_bern":         "sources.new_bern",
    "wilson":           "sources.wilson",
    "fayetteville":     "sources.fayetteville",
    "goldsboro":        "sources.goldsboro",
    "henderson_county": "sources.henderson_county",
    "durham":           "sources.durham_county",
    "lexington":        "sources.lexington",
    "asheville":        "sources.asheville",
    "charlotte":        "sources.charlotte",
    "mecklenburg_county": "sources.meckleburg_county",
    "wilmington":       "sources.wilmington",
    "new_hanover_county": "sources.new_hanover_county",
    "triad":            "sources.triad",
    "google_places":    "sources.google_places",
}


def _import_source(module_path: str):
    """Dynamically import a source module and return it."""
    import importlib
    return importlib.import_module(module_path)


def _ensure_dirs():
    """Create data directories if they don't exist."""
    for d in (_RAW, _PROCESSED, _FINAL, _REFERENCE):
        d.mkdir(parents=True, exist_ok=True)


def _save_json(data, path: Path, label: str):
    """Write data to a JSON file."""
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    logger.info("Wrote %s → %s (%d records)", label, path, len(data))


# ---- Pipeline steps ------------------------------------------------------

def step_fetch(source_names: list[str]) -> dict[str, list[dict]]:
    """Fetch raw data from each source. Returns {source_name: [raw_parks]}."""
    raw_by_source = {}

    for name in source_names:
        module_path = SOURCES.get(name)
        if not module_path:
            logger.error("Unknown source: %s (available: %s)",
                         name, ", ".join(SOURCES))
            continue

        logger.info("━━━ Fetching: %s ━━━", name)
        try:
            mod = _import_source(module_path)
            parks = mod.fetch()
            raw_by_source[name] = parks
            logger.info("  → %d raw records", len(parks))
        except Exception:
            logger.error("Failed to fetch %s", name, exc_info=True)

    return raw_by_source


def step_load_raw(source_names: list[str]) -> dict[str, list[dict]]:
    """Load the most recent raw JSON files instead of fetching."""
    import glob
    raw_by_source = {}

    for name in source_names:
        pattern = str(_RAW / f"{name}_*.json")
        files = sorted(glob.glob(pattern))
        if not files:
            logger.warning("No raw file found for %s — skipping", name)
            continue
        latest = files[-1]
        with open(latest) as f:
            parks = json.load(f)
        raw_by_source[name] = parks
        logger.info("Loaded %d raw records from %s", len(parks),
                    Path(latest).name)

    return raw_by_source


def step_normalize(raw_by_source: dict[str, list[dict]]) -> list[dict]:
    """Normalize all sources into canonical schema."""
    from processing.normalize import normalize

    all_parks = []
    for source_name, raw_parks in raw_by_source.items():
        normalized = normalize(raw_parks, source_name)
        all_parks.extend(normalized)

    logger.info("Total after normalization: %d parks", len(all_parks))
    return all_parks


def step_enrich(parks: list[dict]) -> list[dict]:
    """Add county + geohash to parks."""
    from processing.enrich import enrich

    boundaries_path = _REFERENCE / "nc_counties.geojson"
    return enrich(parks, boundaries_path)


def step_geocode(parks: list[dict], batch_size: int = 0) -> list[dict]:
    """Forward + reverse geocode. batch_size=-1 skips entirely."""
    if batch_size < 0:
        logger.info("Skipping geocode step")
        return parks
    from processing.geocode import geocode
    return geocode(parks, batch_size=batch_size)


def step_validate_urls(parks: list[dict]) -> list[dict]:
    """Validate park URLs and apply overrides."""
    from processing.validate_urls import validate_urls
    return validate_urls(parks)


def step_deduplicate(parks: list[dict]) -> list[dict]:
    """Remove cross-source duplicates."""
    from processing.deduplicate import deduplicate
    return deduplicate(parks)


def step_refresh_boundaries():
    """Re-fetch county boundaries and save to data/reference/."""
    from sources.county_boundaries import fetch, to_geojson

    logger.info("━━━ Refreshing county boundaries ━━━")
    counties = fetch()
    geojson = to_geojson(counties)
    _save_json(geojson, _REFERENCE / "nc_counties.geojson", "county boundaries")
    return counties


def step_load_latest() -> list[dict]:
    """Load the most recent parks_latest.json for reprocessing."""
    latest = _FINAL / "parks_latest.json"
    if not latest.exists():
        logger.error("No parks_latest.json found — run the full pipeline first")
        return []
    with open(latest) as f:
        parks = json.load(f)
    logger.info("Loaded %d parks from %s", len(parks), latest.name)
    return parks


# ---- Main ----------------------------------------------------------------

def run(source_names: list[str] | None = None,
        dry_run: bool = False,
        refresh_boundaries: bool = False,
        geocode_batch: int = 0,
        skip_fetch: bool = False,
        reprocess: bool = False):
    """Run the full pipeline.

    Parameters
    ----------
    source_names:
        Which sources to fetch.  ``None`` = all registered sources.
    dry_run:
        If True, fetch and normalize but don't write final output.
    refresh_boundaries:
        If True, re-download county boundaries before enrichment.
    skip_fetch:
        If True, load from the latest raw files instead of re-fetching.
    reprocess:
        If True, load from parks_latest.json and re-run geocode →
        enrich → validate → dedup → save.  Skips fetch + normalize.
    """
    _ensure_dirs()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")

    if source_names is None:
        source_names = list(SOURCES.keys())

    # 0. Optionally refresh reference data
    if refresh_boundaries or not (_REFERENCE / "nc_counties.geojson").exists():
        step_refresh_boundaries()

    if reprocess:
        # Load existing final output and re-run downstream steps
        all_parks = step_load_latest()
        if not all_parks:
            return
    else:
        # 1. Fetch
        if skip_fetch:
            raw_by_source = step_load_raw(source_names)
        else:
            raw_by_source = step_fetch(source_names)
        if not raw_by_source:
            logger.error("No data fetched — aborting")
            return

        # Save raw data for debugging / reprocessing
        for name, parks in raw_by_source.items():
            _save_json(parks, _RAW / f"{name}_{timestamp}.json", f"raw {name}")

        # 2. Normalize
        all_parks = step_normalize(raw_by_source)

    # 3. Geocode (forward: address→coords, reverse: coords→address)
    all_parks = step_geocode(all_parks, batch_size=geocode_batch)

    # 4. Enrich (all parks now have coordinates)
    all_parks = step_enrich(all_parks)

    # 5. Validate URLs
    all_parks = step_validate_urls(all_parks)

    # Save processed (pre-dedup) snapshot
    _save_json(all_parks, _PROCESSED / f"all_parks_{timestamp}.json", "processed")

    # 5. Deduplicate
    final_parks = step_deduplicate(all_parks)

    if dry_run:
        logger.info("Dry run — skipping final save")
        _print_summary(final_parks)
        return final_parks

    # 5. Save final output
    _save_json(final_parks, _FINAL / f"parks_{timestamp}.json", "final")

    # Also write a "latest" symlink/copy for easy consumption
    latest = _FINAL / "parks_latest.json"
    _save_json(final_parks, latest, "latest")

    # Copy to frontend public dir so the dev server / build picks it up
    frontend_dest = _ROOT.parent / "frontend" / "public" / "data" / "parks_latest.json"
    if frontend_dest.parent.exists():
        import shutil
        shutil.copy2(latest, frontend_dest)
        logger.info("Copied parks_latest.json → %s", frontend_dest)

    _print_summary(final_parks)
    return final_parks


def _print_summary(parks: list[dict]):
    """Print a quick summary table."""
    from collections import Counter
    by_source = Counter(p["source"] for p in parks)
    by_county = Counter(p.get("county") or "Unknown" for p in parks)

    print(f"\n{'='*60}")
    print(f"  Pipeline complete: {len(parks)} parks")
    print(f"{'='*60}")
    print(f"\n  By source:")
    for source, count in by_source.most_common():
        print(f"    {source:20s}  {count:>5}")
    print(f"\n  By county (top 10):")
    for county, count in by_county.most_common(10):
        print(f"    {county:20s}  {count:>5}")
    print()


def main():
    parser = argparse.ArgumentParser(description="NC Parks data pipeline")
    parser.add_argument("--source", "-s", action="append", dest="sources",
                        help="Source to fetch (repeatable). Default: all.")
    parser.add_argument("--dry-run", "-n", action="store_true",
                        help="Fetch and process but don't write final output.")
    parser.add_argument("--refresh-boundaries", action="store_true",
                        help="Re-download county boundary polygons.")
    parser.add_argument("--geocode-batch", type=int, default=0,
                        help="Max geocode API calls (0=unlimited). ~1 req/sec.")
    parser.add_argument("--skip-geocode", action="store_true",
                        help="Skip reverse geocoding step entirely.")
    parser.add_argument("--skip-fetch", action="store_true",
                        help="Load from latest raw files instead of re-fetching.")
    parser.add_argument("--reprocess", action="store_true",
                        help="Re-run geocode/enrich/dedup on parks_latest.json.")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Enable debug logging.")
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)-8s %(name)s: %(message)s")

    geocode_batch = -1 if args.skip_geocode else args.geocode_batch

    run(source_names=args.sources,
        dry_run=args.dry_run,
        refresh_boundaries=args.refresh_boundaries,
        geocode_batch=geocode_batch,
        skip_fetch=args.skip_fetch,
        reprocess=args.reprocess)


if __name__ == "__main__":
    main()
