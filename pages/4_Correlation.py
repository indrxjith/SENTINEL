"""
pages/4_Correlation.py
========================
Cross-asset correlation: full-universe heatmap + table, plus a rolling
pairwise correlation chart for two selected assets.

All values come from data_loader.get_correlation_matrix() and
get_rolling_correlation() — both backend-computed, never recalculated
here.
"""

from __future__ import annotations

import streamlit as st

import data_loader
from components.charts import build_correlation_heatmap, build_rolling_line_chart
from components.navbar import render_navbar
from components.sidebar import render_sidebar
from components.status import not_wired_notice, safe_call
from components.tables import render_correlation_table
from config import APP_TITLE, ASSET_UNIVERSE, COLORS
from theme import apply_theme

st.set_page_config(page_title=f"{APP_TITLE} — Correlation", layout="wide", initial_sidebar_state="expanded")
apply_theme()

selection = render_sidebar()
db_status, _ = safe_call(data_loader.database_is_connected)
render_navbar(selected_asset=selection.asset, db_connected=db_status)

# ---------------------------------------------------------------------------
# Universe heatmap + table
# ---------------------------------------------------------------------------
st.markdown('<div class="sentinel-section-title">Asset Correlation Matrix</div>', unsafe_allow_html=True)

universe_selection = st.multiselect("Assets", options=ASSET_UNIVERSE, default=ASSET_UNIVERSE)

if len(universe_selection) < 2:
    st.markdown(
        '<div class="sentinel-card" style="color: var(--text-secondary);">Select at least two assets.</div>',
        unsafe_allow_html=True,
    )
else:
    corr_matrix, corr_err = safe_call(
        data_loader.get_correlation_matrix, universe_selection, selection.start_date, selection.end_date
    )
    if corr_err:
        not_wired_notice(corr_err)
    else:
        heatmap_col, table_col = st.columns([3, 2])
        with heatmap_col:
            fig = build_correlation_heatmap(corr_matrix)
            st.plotly_chart(fig, use_container_width=True)
        with table_col:
            render_correlation_table(corr_matrix)

# ---------------------------------------------------------------------------
# Rolling pairwise correlation
# ---------------------------------------------------------------------------
st.markdown('<div class="sentinel-section-title">Rolling Correlation</div>', unsafe_allow_html=True)

pair_col_a, pair_col_b, window_col = st.columns([1, 1, 1])
with pair_col_a:
    symbol_a = st.selectbox("Asset A", ASSET_UNIVERSE, index=ASSET_UNIVERSE.index(selection.asset))
with pair_col_b:
    default_b_idx = 1 if ASSET_UNIVERSE[0] == symbol_a else 0
    symbol_b = st.selectbox("Asset B", ASSET_UNIVERSE, index=default_b_idx)
with window_col:
    rolling_window = st.slider("Window (days)", min_value=10, max_value=180, value=63, step=1)

if symbol_a == symbol_b:
    st.markdown(
        '<div class="sentinel-card" style="color: var(--text-secondary);">Select two different assets.</div>',
        unsafe_allow_html=True,
    )
else:
    rolling_corr, rolling_err = safe_call(
        data_loader.get_rolling_correlation,
        symbol_a,
        symbol_b,
        selection.start_date,
        selection.end_date,
        rolling_window,
    )
    if rolling_err:
        not_wired_notice(rolling_err)
    else:
        fig = build_rolling_line_chart(
            rolling_corr, name=f"{symbol_a} / {symbol_b}", color=COLORS.purple, y_title="Correlation"
        )
        st.plotly_chart(fig, use_container_width=True)
