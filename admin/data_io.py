"""Shared data loading and override I/O for the admin review tool."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus

_ROOT = Path(__file__).resolve().parent.parent
_DATA = _ROOT / "data"
_FINAL = _DATA / "final"
_OVERRIDES = _DATA / "overrides"

AMENITY_COLS = [
    "playground", "restrooms", "parking", "walking_trails",
    "picnic_tables", "picnic_shelter", "shaded_areas", "drinking_water",
    "ada_accessible", "ball_fields", "basketball_courts", "tennis_courts",
    "multipurpose_field", "swimming_pool", "splash_pad", "dog_park",
    "disc_golf", "fishing", "skate_park", "bbq_grill",
    "sand_volleyball", "bocce", "horseshoe", "bmx_track",
    "equestrian", "lighting", "greenway_access", "gym",
    "community_center", "camping", "biking", "gardens",
    "fenced_playground", "open_field", "track",
]


def pretty(name: str) -> str:
    return name.replace("_", " ").title()


def park_key(park: dict) -> str:
    return f"{park['source']}::{park['source_id']}"


# ---- Data loading --------------------------------------------------------

def load_parks() -> list[dict]:
    """Load parks with all pending overrides applied (edits, merges, deletions).

    This gives every admin page the same "effective" view of the data —
    manually merged parks appear as one, deleted parks are excluded, and
    field edits are overlaid.
    """
    path = _FINAL / "parks_latest.json"
    if not path.exists():
        return []
    parks = json.loads(path.read_text(encoding="utf-8"))

    # 1. Apply field edits
    edits = _load_json(_OVERRIDES / "field_edits.json", {})
    if edits:
        for p in parks:
            pk = park_key(p)
            if pk in edits:
                for field, value in edits[pk].items():
                    if field == "amenities" and isinstance(value, dict):
                        p.setdefault("amenities", {}).update(value)
                    elif field == "extras" and isinstance(value, dict):
                        p.setdefault("extras", {}).update(value)
                    else:
                        p[field] = value

    # 2. Apply manual merges
    merges: list[dict] = _load_json(_OVERRIDES / "manual_merges.json", [])
    if merges:
        key_to_park = {park_key(p): p for p in parks}
        drop_keys: set[str] = set()
        for m in merges:
            keep_key = m.get("keep", "")
            drop_key = m.get("drop", "")
            if drop_key == "__skip__":
                continue  # "not a duplicate" marker
            primary = key_to_park.get(keep_key)
            secondary = key_to_park.get(drop_key)
            if not primary or not secondary:
                continue

            # Track all_sources
            sources = list(primary.get("all_sources", [
                {"source": primary["source"], "source_id": primary["source_id"]},
            ]))
            sec_entry = {"source": secondary["source"], "source_id": secondary["source_id"]}
            if sec_entry not in sources:
                sources.append(sec_entry)
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
            for field, value in m.get("field_overrides", {}).items():
                primary[field] = value

            drop_keys.add(drop_key)

        if drop_keys:
            parks = [p for p in parks if park_key(p) not in drop_keys]

    # 3. Apply deletions
    deletions: list[str] = _load_json(_OVERRIDES / "deletions.json", [])
    if deletions:
        del_set = set(deletions)
        parks = [p for p in parks if park_key(p) not in del_set]

    return parks


# ---- Override file I/O ---------------------------------------------------

def _ensure_overrides():
    _OVERRIDES.mkdir(parents=True, exist_ok=True)


def _load_json(path: Path, default):
    if not path.exists():
        return default
    text = path.read_text(encoding="utf-8").strip()
    return json.loads(text) if text else default


def _save_json(path: Path, data):
    _ensure_overrides()
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_deletions() -> list[str]:
    return _load_json(_OVERRIDES / "deletions.json", [])


def save_deletions(deletions: list[str]):
    _save_json(_OVERRIDES / "deletions.json", deletions)


def load_field_edits() -> dict[str, dict]:
    return _load_json(_OVERRIDES / "field_edits.json", {})


def save_field_edits(edits: dict[str, dict]):
    _save_json(_OVERRIDES / "field_edits.json", edits)


def load_manual_merges() -> list[dict]:
    return _load_json(_OVERRIDES / "manual_merges.json", [])


def save_manual_merges(merges: list[dict]):
    _save_json(_OVERRIDES / "manual_merges.json", merges)


def load_verifications() -> dict[str, dict]:
    return _load_json(_OVERRIDES / "verifications.json", {})


def save_verifications(verifications: dict[str, dict]):
    _save_json(_OVERRIDES / "verifications.json", verifications)


# ---- URL helpers ---------------------------------------------------------

def google_maps_url(lat: float, lon: float) -> str:
    return f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"


def google_satellite_url(name: str, lat: float, lon: float) -> str:
    return (f"https://www.google.com/maps/place/{quote_plus(name)}"
            f"/@{lat},{lon},100m/data=!3m1!1e3")


def apple_maps_url(name: str, lat: float, lon: float) -> str:
    return f"https://maps.apple.com/?ll={lat},{lon}&q={quote_plus(name)}"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
