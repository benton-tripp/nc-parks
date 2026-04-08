"""NC Parks Admin Review Tool — Streamlit app.

Run from the project root:
    streamlit run admin/app.py
"""

import streamlit as st

st.set_page_config(
    page_title="NC Parks Admin",
    page_icon="🌲",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Page imports (after set_page_config)
from views import dashboard, park_review, dedup_review, deletions  # noqa: E402

PAGES = {
    "Dashboard": dashboard.render,
    "Park Review": park_review.render,
    "Dedup Review": dedup_review.render,
    "Deletions": deletions.render,
}

st.sidebar.title("🌲 NC Parks Admin")
page = st.sidebar.radio("Navigate", list(PAGES.keys()), label_visibility="collapsed")

PAGES[page]()
