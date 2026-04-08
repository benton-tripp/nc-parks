"""Dedup Review — find and resolve potential duplicate parks."""

from __future__ import annotations

import math
import sys
from difflib import SequenceMatcher
from pathlib import Path

import folium
import streamlit as st
from streamlit_folium import st_folium

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from data_io import (
    load_parks, load_manual_merges, save_manual_merges, load_deletions,
    save_deletions, deletion_key_set, load_verifications, park_key,
    google_maps_url, google_satellite_url, pretty, AMENITY_COLS, now_iso,
)


def _haversine_m(lat1, lon1, lat2, lon2):
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _name_sim(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _find_candidates(parks, max_dist=500, min_sim=0.50, limit=200):
    """Find potential duplicate pairs."""
    # Build index by geohash bucket for performance
    candidates = []
    merged_keys = set()
    for p in parks:
        for s in p.get("all_sources", []):
            merged_keys.add(f"{s['source']}::{s['source_id']}")

    # Simple O(n²) scan with early distance rejection (~0.005° ≈ 500m)
    deg_threshold = max_dist / 111_000  # rough degrees
    for i in range(len(parks)):
        if len(candidates) >= limit:
            break
        a = parks[i]
        lat_a, lon_a = a.get("latitude"), a.get("longitude")
        if not lat_a or not lon_a:
            continue
        for j in range(i + 1, len(parks)):
            if len(candidates) >= limit:
                break
            b = parks[j]
            lat_b, lon_b = b.get("latitude"), b.get("longitude")
            if not lat_b or not lon_b:
                continue
            if abs(lat_a - lat_b) > deg_threshold or abs(lon_a - lon_b) > deg_threshold:
                continue
            dist = _haversine_m(lat_a, lon_a, lat_b, lon_b)
            if dist > max_dist:
                continue
            sim = _name_sim(a["name"], b["name"])
            if sim < min_sim:
                continue
            candidates.append({
                "a": a, "b": b,
                "distance_m": round(dist),
                "name_similarity": round(sim * 100),
            })

    candidates.sort(key=lambda c: (-c["name_similarity"], c["distance_m"]))
    return candidates


def _park_summary(park: dict) -> dict:
    """Extract key info for display."""
    extras = park.get("extras", {})
    amenities = park.get("amenities", {})
    active = [pretty(k) for k, v in amenities.items() if v]
    return {
        "Name": park.get("name", ""),
        "Source": park.get("source", ""),
        "Source ID": park.get("source_id", ""),
        "Address": park.get("address", ""),
        "City": park.get("city", ""),
        "County": park.get("county", ""),
        "Lat": park.get("latitude"),
        "Lon": park.get("longitude"),
        "Phone": park.get("phone", ""),
        "URL": park.get("url", ""),
        "Google Rating": extras.get("google_rating"),
        "Google Reviews": extras.get("google_rating_count"),
        "Google Place ID": extras.get("google_place_id"),
        "Amenities": ", ".join(active) if active else "None",
        "Amenity Count": len(active),
    }


def render():
    st.header("Dedup Review")

    parks = load_parks()
    if not parks:
        st.warning("No parks data found.")
        return

    merges = load_manual_merges()
    deletions = load_deletions()
    verifications = load_verifications()
    existing_merge_keys = set()
    for m in merges:
        existing_merge_keys.add(m.get("keep", ""))
        existing_merge_keys.add(m.get("drop", ""))

    # ---- Settings ----
    with st.sidebar:
        st.subheader("Dedup Settings")
        max_dist = st.slider("Max distance (m)", 50, 2500, 300, step=50)
        min_sim = st.slider("Min name similarity (%)", 20, 95, 50, step=5)
        max_pairs = len(parks)
        limit = st.number_input("Max pairs to scan", 50, max_pairs, max_pairs, step=50)

    # ---- Find candidates ----
    with st.spinner("Scanning for potential duplicates..."):
        candidates = _find_candidates(parks, max_dist=max_dist, min_sim=min_sim / 100, limit=limit)

    # Filter out already-merged or deleted pairs
    del_set = deletion_key_set(deletions)
    candidates = [
        c for c in candidates
        if park_key(c["a"]) not in existing_merge_keys
        and park_key(c["b"]) not in existing_merge_keys
        and park_key(c["a"]) not in del_set
        and park_key(c["b"]) not in del_set
    ]

    st.write(f"**{len(candidates)}** potential duplicate pairs found")

    if not candidates:
        st.success("No unresolved duplicate candidates at these thresholds.")

        # Threshold suggestions
        st.subheader("Threshold Analysis")
        st.info(
            "If you've been manually merging many pairs, consider adjusting "
            "`deduplicate.py` thresholds. Current tiers:\n"
            "- 90% similarity → 500m\n"
            "- 80% similarity → 300m\n"
            "- 70% similarity → 100m"
        )
        return

    # ---- Pair selector ----
    pair_labels = [
        f"{c['a']['name']} ↔ {c['b']['name']} ({c['name_similarity']}%, {c['distance_m']}m)"
        for c in candidates
    ]
    pair_idx = st.selectbox("Select pair to review", range(len(candidates)),
                            format_func=lambda i: pair_labels[i])
    cand = candidates[pair_idx]
    park_a, park_b = cand["a"], cand["b"]

    st.divider()
    st.markdown(f"**{cand['name_similarity']}%** name match · **{cand['distance_m']}m** apart")

    # ---- Side-by-side comparison ----
    col_a, col_b = st.columns(2)
    sum_a = _park_summary(park_a)
    sum_b = _park_summary(park_b)

    with col_a:
        st.markdown(f"### Park A")
        has_google_a = bool(sum_a.get("Google Place ID"))
        if has_google_a:
            st.markdown("🌟 **Has Google Places data**")
        for field, val in sum_a.items():
            if val:
                st.text(f"{field}: {val}")
        if park_a.get("latitude") and park_a.get("longitude"):
            st.markdown(f"[Google Maps]({google_maps_url(park_a['latitude'], park_a['longitude'])}) · "
                        f"[Satellite]({google_satellite_url(park_a['name'], park_a['latitude'], park_a['longitude'])})")

    with col_b:
        st.markdown(f"### Park B")
        has_google_b = bool(sum_b.get("Google Place ID"))
        if has_google_b:
            st.markdown("🌟 **Has Google Places data**")
        for field, val in sum_b.items():
            if val:
                st.text(f"{field}: {val}")
        if park_b.get("latitude") and park_b.get("longitude"):
            st.markdown(f"[Google Maps]({google_maps_url(park_b['latitude'], park_b['longitude'])}) · "
                        f"[Satellite]({google_satellite_url(park_b['name'], park_b['latitude'], park_b['longitude'])})")

    # ---- Map showing both ----
    lat_a, lon_a = park_a.get("latitude"), park_a.get("longitude")
    lat_b, lon_b = park_b.get("latitude"), park_b.get("longitude")
    if lat_a and lon_a and lat_b and lon_b:
        center_lat = (lat_a + lat_b) / 2
        center_lon = (lon_a + lon_b) / 2
        m = folium.Map(location=[center_lat, center_lon], zoom_start=16)
        folium.TileLayer(
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            attr="Esri", name="Satellite", overlay=False,
        ).add_to(m)
        folium.LayerControl().add_to(m)
        folium.Marker([lat_a, lon_a], popup=f"A: {park_a['name']}",
                       icon=folium.Icon(color="green")).add_to(m)
        folium.Marker([lat_b, lon_b], popup=f"B: {park_b['name']}",
                       icon=folium.Icon(color="red")).add_to(m)
        st_folium(m, width=700, height=350)

    st.divider()

    # ---- Field-by-field merge builder ----
    st.subheader("Merge Builder")
    st.caption("Pick which park's value to use for each field. Amenities are always unioned. "
               "Google Places extras are carried from whichever has them.")

    key_a = park_key(park_a)
    key_b = park_key(park_b)
    has_google_a = bool((park_a.get("extras") or {}).get("google_place_id"))
    has_google_b = bool((park_b.get("extras") or {}).get("google_place_id"))

    # Fields available for cherry-picking
    _MERGE_FIELDS = [
        ("name", "Name"),
        ("address", "Address"),
        ("city", "City"),
        ("county", "County"),
        ("coords", "Coordinates"),
        ("phone", "Phone"),
        ("url", "URL / Website"),
    ]

    # Smart defaults: prefer non-empty, prefer Google Places source
    def _pick_default(field: str) -> str:
        if field == "coords":
            val_a = park_a.get("latitude") and park_a.get("longitude")
            val_b = park_b.get("latitude") and park_b.get("longitude")
        else:
            val_a = park_a.get(field)
            val_b = park_b.get(field)
        if val_a and not val_b:
            return "A"
        if val_b and not val_a:
            return "B"
        # Both have values — prefer Google Places source
        if has_google_a and not has_google_b:
            return "A"
        if has_google_b and not has_google_a:
            return "B"
        return "A"

    def _display_val(park, field):
        if field == "coords":
            lat, lon = park.get("latitude"), park.get("longitude")
            return f"{lat}, {lon}" if lat and lon else ""
        return str(park.get(field, "") or "")

    selections = {}
    for field_key, label in _MERGE_FIELDS:
        val_a = _display_val(park_a, field_key)
        val_b = _display_val(park_b, field_key)
        default = _pick_default(field_key)
        default_idx = 0 if default == "A" else 1

        cols = st.columns([1, 2, 2, 1])
        with cols[0]:
            st.markdown(f"**{label}**")
        with cols[1]:
            st.text(val_a or "(empty)")
        with cols[2]:
            st.text(val_b or "(empty)")
        with cols[3]:
            choice = st.radio(
                label, ["A", "B"], index=default_idx,
                horizontal=True, key=f"merge_{field_key}",
                label_visibility="collapsed",
            )
        selections[field_key] = choice

    # Amenities & extras info
    amen_a = [pretty(k) for k, v in park_a.get("amenities", {}).items() if v]
    amen_b = [pretty(k) for k, v in park_b.get("amenities", {}).items() if v]
    all_amen = sorted(set(amen_a + amen_b))
    st.markdown(f"**Amenities** — union of both: {', '.join(all_amen) if all_amen else 'None'}")
    if has_google_a or has_google_b:
        gp_src = "A" if has_google_a else "B"
        st.markdown(f"**Google Places data** — from Park {gp_src} (always preserved)")
    st.markdown(f"**Sources** — both parks' sources will be included in `all_sources`")

    st.divider()

    # ---- Action buttons ----
    col1, col2 = st.columns(2)

    with col1:
        if st.button("💾 Save Merge", type="primary"):
            # Determine which park to "keep" as base (the one picked for more fields)
            a_count = sum(1 for v in selections.values() if v == "A")
            b_count = sum(1 for v in selections.values() if v == "B")
            if a_count >= b_count:
                keep_key, drop_key = key_a, key_b
                keep_park, other_park = park_a, park_b
                keep_side = "A"
            else:
                keep_key, drop_key = key_b, key_a
                keep_park, other_park = park_b, park_a
                keep_side = "B"

            # Build field_overrides for any field picked from the "other" park
            overrides = {}
            for field_key, _label in _MERGE_FIELDS:
                if selections[field_key] == keep_side:
                    continue  # already on the kept park
                # Pull value from the other park
                if field_key == "coords":
                    lat = other_park.get("latitude")
                    lon = other_park.get("longitude")
                    if lat is not None:
                        overrides["latitude"] = lat
                    if lon is not None:
                        overrides["longitude"] = lon
                else:
                    val = other_park.get(field_key)
                    if val is not None:
                        overrides[field_key] = val

            merges.append({
                "keep": keep_key,
                "drop": drop_key,
                "field_overrides": overrides,
                "merged_at": now_iso(),
            })
            save_manual_merges(merges)
            kept_name = overrides.get("name", keep_park.get("name", ""))
            st.success(f"Merge saved: **{kept_name}** (base={keep_side}, "
                       f"{len(overrides)} field override(s))")
            st.rerun()

    with col2:
        if st.button("↔️ Not Duplicates — Keep Both"):
            merges.append({"keep": key_a, "drop": "__skip__",
                           "note": f"Reviewed: not a duplicate with {key_b}",
                           "merged_at": now_iso()})
            merges.append({"keep": key_b, "drop": "__skip__",
                           "note": f"Reviewed: not a duplicate with {key_a}",
                           "merged_at": now_iso()})
            save_manual_merges(merges)
            st.info("Marked as reviewed — not duplicates.")
            st.rerun()

    # ---- Delete options ----
    st.divider()
    st.subheader("Delete")
    del_col1, del_col2, del_col3 = st.columns(3)

    with del_col1:
        if st.button(f"🗑️ Delete A ({park_a['name'][:30]})", key="del_a"):
            dk_set = deletion_key_set(deletions)
            if key_a not in dk_set:
                deletions.append({"key": key_a, "deleted_at": now_iso(), "name": park_a["name"]})
                save_deletions(deletions)
            st.success(f"Marked for deletion: {park_a['name']}")
            st.rerun()

    with del_col2:
        if st.button(f"🗑️ Delete B ({park_b['name'][:30]})", key="del_b"):
            dk_set = deletion_key_set(deletions)
            if key_b not in dk_set:
                deletions.append({"key": key_b, "deleted_at": now_iso(), "name": park_b["name"]})
                save_deletions(deletions)
            st.success(f"Marked for deletion: {park_b['name']}")
            st.rerun()

    with del_col3:
        if st.button("🗑️ Delete Both", key="del_both"):
            dk_set = deletion_key_set(deletions)
            changed = False
            for k, name in ((key_a, park_a["name"]), (key_b, park_b["name"])):
                if k not in dk_set:
                    deletions.append({"key": k, "deleted_at": now_iso(), "name": name})
                    changed = True
            if changed:
                save_deletions(deletions)
            st.success(f"Marked both for deletion: {park_a['name']} & {park_b['name']}")
            st.rerun()

    # ---- Threshold suggestions ----
    if len(merges) >= 5:
        real_merges = [m for m in merges if m.get("drop") != "__skip__"]
        if len(real_merges) >= 5:
            st.divider()
            st.subheader("Threshold Suggestions")
            st.info(
                f"You've manually merged **{len(real_merges)}** pairs. "
                f"Review whether `deduplicate.py` thresholds should be adjusted. "
                f"Current: 90%/500m, 80%/300m, 70%/100m."
            )
