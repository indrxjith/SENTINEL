"""
pages/6_Database.py
======================
Raw repository data browser: search, sort, filter, paginate, and export
to CSV. No analytics, no risk metrics — this page exists so an analyst
can inspect exactly what's in PostgreSQL for the selected assets/range.
"""

from __future__ import annotations

import streamlit as st

import data_loader
from components.navbar import render_navbar
from components.sidebar import render_sidebar
from components.status import not_wired_notice, safe_call
from components.tables import render_explorer_table
from config import APP_TITLE, ASSET_UNIVERSE
from theme import apply_theme

st.set_page_config(page_title=f"{APP_TITLE} — Database Explorer", layout="wide", initial_sidebar_state="expanded")
apply_theme()

selection = render_sidebar()
db_status, _ = safe_call(data_loader.database_is_connected)
render_navbar(selected_asset=selection.asset, db_connected=db_status)

st.markdown('<div class="sentinel-section-title">Raw Market Data</div>', unsafe_allow_html=True)

symbols = st.multiselect("Symbols", options=ASSET_UNIVERSE, default=[selection.asset])

if not symbols:
    st.markdown(
        '<div class="sentinel-card" style="color: var(--text-secondary);">Select at least one symbol.</div>',
        unsafe_allow_html=True,
    )
else:
    table_df, table_err = safe_call(
        data_loader.get_market_data_table, symbols, selection.start_date, selection.end_date
    )
    if table_err:
        not_wired_notice(table_err)
    else:
        render_explorer_table(table_df, key_prefix="market_data")
