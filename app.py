"""
app.py
======
SENTINEL entry point.

Streamlit automatically discovers all pages inside the `pages/`
directory. This file configures the application, applies the global
theme, and renders the landing screen.
"""

from __future__ import annotations

import datetime as dt

import streamlit as st

import data_loader
from components.navbar import render_navbar
from components.status import safe_call
from config import APP_SUBTITLE, APP_TITLE, ASSET_UNIVERSE, DEFAULT_ASSET
from theme import apply_theme

st.set_page_config(
    page_title=f"{APP_TITLE} — Market Risk Intelligence",
    page_icon="assets/logo.svg",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_theme()

db_status, _ = safe_call(data_loader.database_is_connected)
render_navbar(selected_asset=DEFAULT_ASSET, db_connected=db_status)

# ---------------------------------------------------------------------------
# Hero
# ---------------------------------------------------------------------------
now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

st.markdown(
    f"""
    <div class="sentinel-hero">
        <div class="sentinel-hero__title">{APP_TITLE}</div>
        <div class="sentinel-hero__subtitle">{APP_SUBTITLE}</div>
        <div class="sentinel-hero__meta">
            <span>UNIVERSE: {len(ASSET_UNIVERSE)} assets ({', '.join(ASSET_UNIVERSE)})</span>
            <span>SESSION: {now}</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Page grid — each card links straight into that page
# ---------------------------------------------------------------------------
st.markdown('<div class="sentinel-section-title">Modules</div>', unsafe_allow_html=True)

PAGES = [
    {
        "path": "pages/1_Overview.py",
        "title": "Overview",
        "desc": "Portfolio snapshot — composite risk score, latest price, and recent risk events for the selected asset.",
    },
    {
        "path": "pages/2_Risk_Analytics.py",
        "title": "Risk Analytics",
        "desc": "Value at Risk, Expected Shortfall, rolling volatility, and beta against a benchmark.",
    },
    {
        "path": "pages/3_Model_Validation.py",
        "title": "Model Validation",
        "desc": "Kupiec, Christoffersen, and Conditional Coverage backtests, plus the Basel rolling traffic light.",
    },
    {
        "path": "pages/4_Correlation.py",
        "title": "Correlation",
        "desc": "Cross-asset correlation matrix and rolling pairwise correlation over time.",
    },
    {
        "path": "pages/5_Regime_Analysis.py",
        "title": "Regime Analysis",
        "desc": "Market regime classification timeline for the selected asset.",
    },
    {
        "path": "pages/6_Database.py",
        "title": "Database Explorer",
        "desc": "Raw market data — search, sort, filter, and export directly from PostgreSQL.",
    },
]

cols = st.columns(3)
for i, page in enumerate(PAGES):
    with cols[i % 3]:
        st.markdown(
            f"""
            <div class="sentinel-page-card">
                <div class="sentinel-page-card__title">{page['title']}</div>
                <div class="sentinel-page-card__desc">{page['desc']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.page_link(page["path"], label="Open →", use_container_width=True)