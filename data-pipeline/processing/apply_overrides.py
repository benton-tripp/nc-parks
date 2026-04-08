"""Apply manual overrides to park data.

Reads JSON override files from data/overrides/ and applies them in order:
  1. Deletions  — remove parks by key
  2. Merges     — merge park B into park A
  3. Field edits — overwrite individual fields
  4. Verifications — stamp verification status into extras

Override files are keyed by ``source::source_id``.

This module is called by the pipeline after dedup, before final output.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_OVERRIDES = Path(__file__).resolve().parent.parent.parent / "data" / "overrides"


def _park_key(park: dict) -> str:
    """Canonical key for a park: ``source::source_id``."""
    return f"{park['source']}::{park['source_id']}"


def _load_json(path: Path, default):
    """Load a JSON file, returning *default* if missing or empty."""
    if not path.exists():
        return default
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return default
    return json.loads(text)


def apply_overrides(
    parks: list[dict],
    overrides_dir: Path | None = None,
) -> list[dict]:
    """Apply all override files to *parks* and return the modified list.

    Parameters
    ----------
    parks:
        Deduplicated park list.
    overrides_dir:
        Path to the overrides folder.  Defaults to ``data/overrides/``.
    """
    d = overrides_dir or _OVERRIDES
    deletions: list[str] = _load_json(d / "deletions.json", [])
    merges: list[dict] = _load_json(d / "manual_merges.json", [])
    edits: dict[str, dict] = _load_json(d / "field_edits.json", {})
    verifications: dict[str, dict] = _load_json(d / "verifications.json", {})

    n_del = n_merge = n_edit = n_verify = 0

    # --- 1. Deletions -------------------------------------------------------
    if deletions:
        del_set = {(d["key"] if isinstance(d, dict) else d) for d in deletions}
        before = len(parks)
        parks = [p for p in parks if _park_key(p) not in del_set]
        n_del = before - len(parks)

    # --- 2. Manual merges ----------------------------------------------------
    if merges:
        key_to_park: dict[str, dict] = {_park_key(p): p for p in parks}
        drop_keys: set[str] = set()
        for m in merges:
            keep_key = m.get("keep", "")
            drop_key = m.get("drop", "")
            overrides = m.get("field_overrides", {})
            primary = key_to_park.get(keep_key)
            secondary = key_to_park.get(drop_key)
            if not primary:
                logger.warning("Merge: keep key %r not found — skipping", keep_key)
                continue
            if not secondary:
                logger.warning("Merge: drop key %r not found — skipping", drop_key)
                continue

            # Track all_sources
            sources = primary.get("all_sources", [
                {"source": primary["source"], "source_id": primary["source_id"]},
            ])
            sources.append({"source": secondary["source"], "source_id": secondary["source_id"]})
            primary["all_sources"] = sources

            # Merge amenities (True wins)
            for k, v in secondary.get("amenities", {}).items():
                if v is True:
                    primary.setdefault("amenities", {})[k] = True

            # Fill blanks from secondary
            for field in ("address", "city", "county", "phone", "url"):
                if not primary.get(field) and secondary.get(field):
                    primary[field] = secondary[field]

            # Carry over Google extras
            for gk in ("google_rating", "google_rating_count", "google_maps_uri",
                        "google_place_id", "google_types", "google_data_date"):
                if gk not in primary.get("extras", {}) and gk in secondary.get("extras", {}):
                    primary.setdefault("extras", {})[gk] = secondary["extras"][gk]

            # Apply explicit field overrides
            for field, value in overrides.items():
                primary[field] = value

            drop_keys.add(drop_key)
            n_merge += 1

        if drop_keys:
            parks = [p for p in parks if _park_key(p) not in drop_keys]

    # --- 3. Field edits ------------------------------------------------------
    if edits:
        key_to_park = {_park_key(p): p for p in parks}
        for pk, fields in edits.items():
            target = key_to_park.get(pk)
            if not target:
                logger.warning("Field edit: key %r not found — skipping", pk)
                continue
            for field, value in fields.items():
                if field.startswith("_"):  # skip audit metadata
                    continue
                if field == "amenities" and isinstance(value, dict):
                    target.setdefault("amenities", {}).update(value)
                elif field == "extras" and isinstance(value, dict):
                    target.setdefault("extras", {}).update(value)
                else:
                    target[field] = value
            n_edit += 1

    # --- 4. Verification stamps ----------------------------------------------
    if verifications:
        key_to_park = key_to_park if edits else {_park_key(p): p for p in parks}
        for pk, vdata in verifications.items():
            target = key_to_park.get(pk)
            if not target:
                logger.warning("Verification: key %r not found — skipping", pk)
                continue
            target.setdefault("extras", {})["_verification"] = vdata
            n_verify += 1

    # --- Summary -------------------------------------------------------------
    total = n_del + n_merge + n_edit + n_verify
    if total:
        logger.info(
            "Overrides applied: %d deletions, %d merges, %d field edits, %d verifications",
            n_del, n_merge, n_edit, n_verify,
        )
    else:
        logger.info("Overrides: no overrides to apply")

    return parks
