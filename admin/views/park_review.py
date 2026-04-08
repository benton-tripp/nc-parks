"""Park Review — browse, verify, and edit individual parks."""

from __future__ import annotations

import sys
from pathlib import Path

import folium
import streamlit as st
from streamlit_folium import st_folium

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from data_io import (
    AMENITY_COLS, AMENITY_CATEGORIES, AMENITY_LABELS,
    load_parks, load_verifications, save_verifications,
    load_field_edits, save_field_edits, load_deletions, save_deletions,
    deletion_key_set, park_key, pretty, google_maps_url, google_satellite_url,
    apple_maps_url, now_iso,
)


def _get_parks():
    """Load and cache parks list in session state."""
    if "parks" not in st.session_state:
        st.session_state.parks = load_parks()
    return st.session_state.parks


def render():
    st.header("Park Review")

    parks = _get_parks()
    if not parks:
        st.warning("No parks data found.")
        return

    verifications = load_verifications()
    edits = load_field_edits()
    deletions_list = load_deletions()
    del_set = deletion_key_set(deletions_list)

    # ---- Filters ----
    with st.sidebar:
        st.subheader("Filters")

        # Status filter
        status_filter = st.selectbox("Verification status", [
            "All", "Unreviewed", "Verified",
        ])

        # Source filter
        sources = sorted(set(p["source"] for p in parks))
        source_filter = st.selectbox("Source", ["All"] + sources)

        # County filter
        counties = sorted(set(p.get("county") or "Unknown" for p in parks))
        county_filter = st.selectbox("County", ["All"] + counties)

        # Text search
        search = st.text_input("Search by name", "")

        # Data quality filters
        st.subheader("Data Quality")
        only_missing_addr = st.checkbox("Missing address")
        only_no_amenities = st.checkbox("No amenities")
        only_has_google = st.checkbox("Has Google data")
        only_missing_google = st.checkbox("No Google data")

    # ---- Apply filters ----
    filtered = parks
    verified_keys = set(verifications.keys())

    if status_filter == "Unreviewed":
        filtered = [p for p in filtered if park_key(p) not in verified_keys]
    elif status_filter == "Verified":
        filtered = [p for p in filtered if park_key(p) in verified_keys]

    if source_filter != "All":
        filtered = [p for p in filtered if p["source"] == source_filter]
    if county_filter != "All":
        filtered = [p for p in filtered if (p.get("county") or "Unknown") == county_filter]
    if search:
        q = search.lower()
        filtered = [p for p in filtered if q in p["name"].lower()]
    if only_missing_addr:
        filtered = [p for p in filtered if not p.get("address")]
    if only_no_amenities:
        filtered = [p for p in filtered if not any(p.get("amenities", {}).values())]
    if only_has_google:
        filtered = [p for p in filtered if p.get("extras", {}).get("google_place_id")]
    if only_missing_google:
        filtered = [p for p in filtered if not p.get("extras", {}).get("google_place_id")]

    st.write(f"**{len(filtered):,}** parks matching filters")

    if not filtered:
        return

    # ---- Park selector ----
    # Build unique labels: add city/county/coords when names collide
    _name_counts: dict[str, int] = {}
    for p in filtered:
        label = f"{p['name']} ({p['source']})"
        _name_counts[label] = _name_counts.get(label, 0) + 1

    park_names: list[str] = []
    for p in filtered:
        label = f"{p['name']} ({p['source']})"
        if _name_counts[label] > 1:
            city = p.get("city") or p.get("county") or ""
            lat = round(p.get("latitude", 0), 3)
            lon = round(p.get("longitude", 0), 3)
            label += f" — {city} [{lat}, {lon}]" if city else f" [{lat}, {lon}]"
        park_names.append(label)
    idx = st.selectbox("Select a park", range(len(filtered)),
                       format_func=lambda i: park_names[i])
    park = filtered[idx]
    pk = park_key(park)

    st.divider()

    # ---- Park detail ----
    col_detail, col_map = st.columns([3, 2])

    with col_detail:
        is_verified = pk in verified_keys
        status_emoji = "✅" if is_verified else "⬜"
        st.subheader(f"{status_emoji} {park['name']}")

        # Quick links
        lat, lon = park.get("latitude"), park.get("longitude")
        if lat and lon:
            links = (
                f"[Google Maps]({google_maps_url(lat, lon)}) · "
                f"[Satellite]({google_satellite_url(park['name'], lat, lon)}) · "
                f"[Apple Maps]({apple_maps_url(park['name'], lat, lon)})"
            )
            st.markdown(links)

        if park.get("url"):
            st.markdown(f"[Park Website]({park['url']})")
        if park.get("source_url"):
            st.markdown(f"[Source: {park['source']}]({park['source_url']})")

        # ---- Google Places highlight ----
        extras = park.get("extras", {})
        if extras.get("google_place_id"):
            st.markdown("---")
            st.markdown("**🌟 Google Places Data**")
            gcol1, gcol2, gcol3 = st.columns(3)
            gcol1.metric("Rating", f"{extras.get('google_rating', 'N/A')}")
            gcol2.metric("Reviews", f"{extras.get('google_rating_count', 'N/A'):,}" if isinstance(extras.get('google_rating_count'), (int, float)) else "N/A")
            gcol3.metric("Data Date", extras.get("google_data_date", "N/A"))
            if extras.get("google_maps_uri"):
                st.markdown(f"[Google Maps Page]({extras['google_maps_uri']})")
            if extras.get("google_types"):
                st.write("Types:", ", ".join(extras["google_types"]))
            st.markdown("---")

        # All sources (if merged)
        all_sources = park.get("all_sources", [{"source": park["source"], "source_id": park["source_id"]}])
        if len(all_sources) > 1:
            st.write("**Merged from:**")
            for s in all_sources:
                label = s["source"]
                # Highlight Google Places source
                if s["source"] == "google_places":
                    label = f"**🌟 {label}**"
                st.write(f"  - {label} (`{s['source_id']}`)")

        # Core fields
        st.markdown("**Core Fields**")
        field_data = {
            "Name": park.get("name", ""),
            "Address": park.get("address", ""),
            "City": park.get("city", ""),
            "County": park.get("county", ""),
            "State": park.get("state", "NC"),
            "Phone": park.get("phone", ""),
            "Latitude": str(lat or ""),
            "Longitude": str(lon or ""),
        }
        for label, val in field_data.items():
            st.text(f"{label}: {val}")

    with col_map:
        if lat and lon:
            m = folium.Map(location=[lat, lon], zoom_start=16,
                           tiles="OpenStreetMap")
            # Satellite tile layer
            folium.TileLayer(
                tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                attr="Esri",
                name="Satellite",
                overlay=False,
            ).add_to(m)
            folium.LayerControl().add_to(m)

            # Main park marker
            folium.Marker(
                [lat, lon],
                popup=park["name"],
                icon=folium.Icon(color="green", icon="tree-deciduous", prefix="glyphicon"),
            ).add_to(m)

            # Show clicked coordinate marker if set
            clicked_key = f"clicked_coords_{pk}"
            if clicked_key in st.session_state:
                clat, clon = st.session_state[clicked_key]
                folium.Marker(
                    [clat, clon],
                    popup="📍 New location",
                    icon=folium.Icon(color="red", icon="screenshot", prefix="glyphicon"),
                ).add_to(m)

            # Show nearby parks for dedup context (within ~500m)
            for other in parks:
                if park_key(other) == pk:
                    continue
                olat, olon = other.get("latitude"), other.get("longitude")
                if not olat or not olon:
                    continue
                # Rough distance filter (~500m ≈ 0.005 degrees)
                if abs(olat - lat) > 0.005 and abs(olon - lon) > 0.005:
                    continue
                color = "orange" if other.get("extras", {}).get("google_place_id") else "blue"
                folium.CircleMarker(
                    [olat, olon],
                    radius=6,
                    color=color,
                    fill=True,
                    popup=f"{other['name']} ({other['source']})",
                ).add_to(m)

            map_data = st_folium(m, width=400, height=400)

            # Capture click for coordinate correction
            if map_data and map_data.get("last_clicked"):
                new_lat_click = round(map_data["last_clicked"]["lat"], 7)
                new_lon_click = round(map_data["last_clicked"]["lng"], 7)
                st.session_state[clicked_key] = (new_lat_click, new_lon_click)
                st.caption(f"📍 Clicked: {new_lat_click}, {new_lon_click}")
            elif clicked_key in st.session_state:
                clat, clon = st.session_state[clicked_key]
                st.caption(f"📍 Selected: {clat}, {clon}")

            if clicked_key in st.session_state:
                if st.button("Clear clicked location", key="clear_click"):
                    del st.session_state[clicked_key]
                    st.rerun()
        else:
            st.info("No coordinates available. Click the map after adding initial coords.")

    st.divider()

    # ---- Amenities ----
    st.subheader("Amenities")
    amenities = park.get("amenities", {})
    current_edits = edits.get(pk, {}).get("amenities", {})

    edited_amenities = {}
    # Group by category from the registry
    from collections import OrderedDict
    cats: OrderedDict[str, list[str]] = OrderedDict()
    for a in AMENITY_COLS:
        cat = AMENITY_CATEGORIES.get(a, "Other")
        cats.setdefault(cat, []).append(a)
    for cat, keys in cats.items():
        st.caption(cat)
        cols = st.columns(4)
        for i, a in enumerate(keys):
            label = AMENITY_LABELS.get(a, pretty(a))
            current = current_edits.get(a, amenities.get(a, False))
            new_val = cols[i % 4].checkbox(label, value=bool(current), key=f"amenity_{a}")
            if new_val != amenities.get(a, False):
                edited_amenities[a] = new_val

    st.divider()

    # ---- Field editing ----
    st.subheader("Edit Fields")
    current_field_edits = edits.get(pk, {})

    # Use clicked coordinates if available, otherwise fall back to edits/park data
    clicked_key = f"clicked_coords_{pk}"
    if clicked_key in st.session_state:
        default_lat = str(st.session_state[clicked_key][0])
        default_lon = str(st.session_state[clicked_key][1])
    else:
        default_lat = str(current_field_edits.get("latitude", park.get("latitude", "")))
        default_lon = str(current_field_edits.get("longitude", park.get("longitude", "")))

    with st.form("field_edits_form"):
        new_name = st.text_input("Name", value=current_field_edits.get("name", park.get("name", "")))
        new_addr = st.text_input("Address", value=current_field_edits.get("address", park.get("address", "")))
        new_city = st.text_input("City", value=current_field_edits.get("city", park.get("city", "")))
        new_phone = st.text_input("Phone", value=current_field_edits.get("phone", park.get("phone", "")))
        new_url = st.text_input("Website URL (clear to remove)",
                                value=current_field_edits.get("url", park.get("url", "")))

        new_lat = st.text_input("Latitude", value=default_lat)
        new_lon = st.text_input("Longitude", value=default_lon)

        submitted = st.form_submit_button("Save Field Edits", type="primary")
        if submitted:
            changes: dict = {}
            if new_name != park.get("name", ""):
                changes["name"] = new_name
            if new_addr != park.get("address", ""):
                changes["address"] = new_addr
            if new_city != park.get("city", ""):
                changes["city"] = new_city
            if new_phone != park.get("phone", ""):
                changes["phone"] = new_phone
            # URL: save even if empty (to allow clearing)
            if new_url != (park.get("url") or ""):
                changes["url"] = new_url
            try:
                lat_f = float(new_lat)
                if lat_f != park.get("latitude"):
                    changes["latitude"] = lat_f
            except ValueError:
                pass
            try:
                lon_f = float(new_lon)
                if lon_f != park.get("longitude"):
                    changes["longitude"] = lon_f
            except ValueError:
                pass
            if edited_amenities:
                changes["amenities"] = edited_amenities

            if changes:
                edits[pk] = {**current_field_edits, **changes, "_edited_at": now_iso()}
                save_field_edits(edits)
                # Clear clicked coords after saving
                if clicked_key in st.session_state:
                    del st.session_state[clicked_key]
                st.success(f"Saved {len(changes)} field edit(s) for {park['name']}")
            else:
                # Remove any existing edits if nothing changed
                if pk in edits:
                    del edits[pk]
                    save_field_edits(edits)
                st.info("No changes to save.")

    st.divider()

    # ---- Verification ----
    st.subheader("Verification")
    verification = verifications.get(pk, {})
    current_fields = verification.get("fields", {})

    VERIFY_FIELDS = ["name", "address", "coordinates", "phone", "amenities"]
    STATUS_OPTIONS = ["unreviewed", "verified", "corrected", "needs_review", "flagged"]

    vcols = st.columns(len(VERIFY_FIELDS))
    new_field_statuses = {}
    for i, field in enumerate(VERIFY_FIELDS):
        current_status = current_fields.get(field, {}).get("status", "unreviewed")
        idx = STATUS_OPTIONS.index(current_status) if current_status in STATUS_OPTIONS else 0
        new_status = vcols[i].selectbox(
            pretty(field), STATUS_OPTIONS, index=idx, key=f"verify_{field}",
        )
        new_field_statuses[field] = {"status": new_status}
        # Carry over existing notes
        if field in current_fields and "note" in current_fields[field]:
            new_field_statuses[field]["note"] = current_fields[field]["note"]

    verify_note = st.text_input("Verification note (optional)",
                                value=verification.get("note", ""))

    col_verify, col_delete, _ = st.columns([1, 1, 3])

    with col_verify:
        if st.button("Save Verification", type="primary"):
            verifications[pk] = {
                "verified_at": now_iso(),
                "fields": new_field_statuses,
            }
            if verify_note:
                verifications[pk]["note"] = verify_note
            save_verifications(verifications)
            st.success(f"Verification saved for {park['name']}")

    with col_delete:
        if st.button("🗑️ Mark for Deletion", type="secondary"):
            deletions_list.append({
                "key": pk,
                "deleted_at": now_iso(),
                "name": park["name"],
            })
            save_deletions(deletions_list)
            st.warning(f"Marked {park['name']} for deletion")
            st.rerun()
