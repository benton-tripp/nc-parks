"""Deletions — review and manage parks marked for removal."""

from __future__ import annotations

import sys
from pathlib import Path

import folium
import streamlit as st
from streamlit_folium import st_folium

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from data_io import (
    load_parks, load_deletions, save_deletions, park_key,
    google_maps_url, google_satellite_url, pretty, AMENITY_COLS,
)


def render():
    st.header("Deletions")

    parks = load_parks()
    deletions = load_deletions()
    park_map = {park_key(p): p for p in parks}

    # ---- Current deletion list ----
    st.subheader(f"Parks marked for deletion ({len(deletions)})")

    if not deletions:
        st.info("No parks are currently marked for deletion.")
    else:
        for i, key in enumerate(deletions):
            park = park_map.get(key)
            with st.expander(f"{'❌ ' + park['name'] + ' — ' + park.get('source', '') if park else key}"):
                if park:
                    col_l, col_r = st.columns([2, 1])
                    with col_l:
                        st.text(f"Source:    {park.get('source', '')}")
                        st.text(f"Source ID: {park.get('source_id', '')}")
                        st.text(f"Address:   {park.get('address', '')}")
                        st.text(f"City:      {park.get('city', '')}")
                        st.text(f"County:    {park.get('county', '')}")
                        st.text(f"Coords:    {park.get('latitude')}, {park.get('longitude')}")
                        extras = park.get("extras", {})
                        if extras.get("google_place_id"):
                            st.warning("⚠️ This park has Google Places data")
                        amenities = park.get("amenities", {})
                        active = [pretty(k) for k, v in amenities.items() if v]
                        if active:
                            st.text(f"Amenities: {', '.join(active)}")

                    with col_r:
                        lat, lon = park.get("latitude"), park.get("longitude")
                        if lat and lon:
                            m = folium.Map(location=[lat, lon], zoom_start=15)
                            folium.Marker([lat, lon], popup=park["name"],
                                          icon=folium.Icon(color="red")).add_to(m)
                            st_folium(m, width=350, height=250, key=f"del_map_{i}")
                else:
                    st.warning(f"Park key `{key}` not found in current data — "
                               "may have been removed by a source re-scrape.")

                if st.button("🔄 Restore (undelete)", key=f"restore_{i}"):
                    deletions.remove(key)
                    save_deletions(deletions)
                    st.success(f"Restored: {key}")
                    st.rerun()

    st.divider()

    # ---- Quick-add deletion ----
    st.subheader("Quick Delete by Key")
    st.caption("Format: `source::source_id`  — e.g. `nps::great-smoky-mountains`")

    # Source filter for quick browsing
    sources = sorted({p.get("source", "") for p in parks})
    sel_source = st.selectbox("Filter by source", ["(all)"] + sources)

    if sel_source != "(all)":
        filtered = [p for p in parks if p.get("source") == sel_source]
    else:
        filtered = parks

    # Exclude already-deleted parks
    del_set = set(deletions)
    filtered = [p for p in filtered if park_key(p) not in del_set]

    if filtered:
        labels = sorted(
            [(f"{p['name']} [{p.get('source')}::{p.get('source_id', '')}]", park_key(p)) for p in filtered],
            key=lambda x: x[0],
        )
        sel = st.selectbox("Select park to delete", range(len(labels)),
                           format_func=lambda i: labels[i][0])
        chosen_key = labels[sel][1]
        chosen_park = park_map.get(chosen_key)

        if chosen_park:
            col1, col2 = st.columns(2)
            with col1:
                st.text(f"Name:    {chosen_park.get('name')}")
                st.text(f"Source:  {chosen_park.get('source')}")
                st.text(f"Address: {chosen_park.get('address', '')}")
                st.text(f"County:  {chosen_park.get('county', '')}")
                extras = chosen_park.get("extras", {})
                if extras.get("google_place_id"):
                    st.warning("⚠️ Park has Google Places data")
            with col2:
                lat, lon = chosen_park.get("latitude"), chosen_park.get("longitude")
                if lat and lon:
                    m = folium.Map(location=[lat, lon], zoom_start=15)
                    folium.Marker([lat, lon], popup=chosen_park["name"],
                                  icon=folium.Icon(color="orange")).add_to(m)
                    st_folium(m, width=350, height=250, key="quick_del_map")

        if st.button("🗑️ Mark for deletion", type="primary"):
            deletions.append(chosen_key)
            save_deletions(deletions)
            st.success(f"Marked for deletion: {chosen_key}")
            st.rerun()
    else:
        st.info("No parks available (all deleted or no source selected).")

    # ---- Summary ----
    st.divider()
    st.subheader("Deletion Impact")
    st.metric("Parks to remove on next pipeline run", len(deletions))
    st.caption("Deletions are applied during the `apply_overrides` pipeline step.")
