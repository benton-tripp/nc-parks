"""Dashboard — verification progress, data quality stats, override summary."""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from data_io import load_parks, load_verifications, load_deletions, load_field_edits, load_manual_merges, park_key


def render():
    st.header("Dashboard")

    parks = load_parks()
    if not parks:
        st.warning("No parks data found. Run the pipeline first.")
        return

    verifications = load_verifications()
    deletions = load_deletions()
    edits = load_field_edits()
    merges = load_manual_merges()

    # ---- Top-level metrics ----
    n_verified = len(verifications)
    n_deleted = len(deletions)
    n_edited = len(edits)
    n_merged = len(merges)

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Parks", f"{len(parks):,}")
    col2.metric("Verified", f"{n_verified:,}")
    col3.metric("Field Edits", f"{n_edited:,}")
    col4.metric("Manual Merges", f"{n_merged:,}")
    col5.metric("Deletions", f"{n_deleted:,}")

    st.divider()

    # ---- By-source breakdown ----
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Parks by Source")
        by_source = Counter(p["source"] for p in parks)
        verified_keys = set(verifications.keys())
        source_data = []
        for source, count in by_source.most_common():
            source_parks = [p for p in parks if p["source"] == source]
            v_count = sum(1 for p in source_parks if park_key(p) in verified_keys)
            pct = f"{v_count / count * 100:.0f}%" if count else "0%"
            source_data.append({
                "Source": source,
                "Count": count,
                "Verified": v_count,
                "% Done": pct,
            })
        st.dataframe(source_data, width='stretch', hide_index=True)

    with col_right:
        st.subheader("Parks by County (top 20)")
        by_county = Counter(p.get("county") or "Unknown" for p in parks)
        county_data = []
        for county, count in by_county.most_common(20):
            county_parks = [p for p in parks if (p.get("county") or "Unknown") == county]
            v_count = sum(1 for p in county_parks if park_key(p) in verified_keys)
            pct = f"{v_count / count * 100:.0f}%" if count else "0%"
            county_data.append({
                "County": county,
                "Count": count,
                "Verified": v_count,
                "% Done": pct,
            })
        st.dataframe(county_data, width='stretch', hide_index=True)

    st.divider()

    # ---- Data quality flags ----
    st.subheader("Data Quality Flags")
    missing_addr = [p for p in parks if not p.get("address")]
    missing_county = [p for p in parks if not p.get("county")]
    missing_coords = [p for p in parks if not p.get("latitude") or not p.get("longitude")]
    no_amenities = [p for p in parks if not any(p.get("amenities", {}).values())]
    has_google = [p for p in parks if p.get("extras", {}).get("google_place_id")]

    q1, q2, q3, q4, q5 = st.columns(5)
    q1.metric("Missing Address", len(missing_addr))
    q2.metric("Missing County", len(missing_county))
    q3.metric("Missing Coords", len(missing_coords))
    q4.metric("No Amenities", len(no_amenities))
    q5.metric("Has Google Data", f"{len(has_google):,}")

    # ---- Google Places coverage ----
    st.divider()
    st.subheader("Google Places Coverage")
    google_parks = [p for p in parks if p["source"] == "google_places"]
    merged_with_google = [p for p in parks if p.get("extras", {}).get("google_place_id") and p["source"] != "google_places"]
    st.write(f"**{len(google_parks):,}** standalone Google Places parks")
    st.write(f"**{len(merged_with_google):,}** other parks merged with Google Places data (have ratings/reviews)")
    st.write(f"**{len(has_google):,}** total parks with Google Place ID")
