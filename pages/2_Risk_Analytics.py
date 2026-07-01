"""
pages/2_Risk_Analytics.py
==========================
Deeper risk views for the selected asset: rolling VaR, rolling Expected
Shortfall, rolling volatility, return distribution, drawdown, and tail
losses.

Rolling VaR/ES/volatility come straight from data_loader (backend-
computed). Distribution, drawdown, and tail losses are derived from the
raw price/return series in services/derived.py — see that module's
docstring for why those are safe to compute client-side.
"""

from __future__ import annotations

import streamlit as st

import data_loader
from components.charts import (
    build_distribution_histogram,
    build_drawdown_chart,
    build_rolling_line_chart,
)
from components.navbar import render_navbar
from components.sidebar import render_sidebar
from components.status import not_wired_notice, safe_call
from components.tables import render_tail_losses_table
from config import APP_TITLE, COLORS
from services.derived import compute_drawdown, compute_returns, compute_tail_losses
from theme import apply_theme

st.set_page_config(page_title=f"{APP_TITLE} — Risk Analytics", layout="wide", initial_sidebar_state="expanded")
apply_theme()

selection = render_sidebar()
db_status, _ = safe_call(data_loader.database_is_connected)
render_navbar(selected_asset=selection.asset, db_connected=db_status)

method_key = selection.model.lower().replace(" ", "_")
if method_key not in ("historical", "parametric"):
    method_key = "historical"

vol_window = st.slider("Volatility window (days)", min_value=5, max_value=90, value=21, step=1)

price_df, price_err = safe_call(data_loader.get_price_history, selection.asset, selection.start_date, selection.end_date)
var_df, var_err = safe_call(data_loader.get_var, selection.asset, method_key, selection.start_date, selection.end_date)
es_df, es_err = safe_call(data_loader.get_expected_shortfall, selection.asset, selection.start_date, selection.end_date)
vol_series, vol_err = safe_call(
    data_loader.get_rolling_volatility, selection.asset, selection.start_date, selection.end_date, vol_window
)

# ---------------------------------------------------------------------------
# Rolling VaR / Rolling Expected Shortfall
# ---------------------------------------------------------------------------
var_col, es_col = st.columns(2)

with var_col:
    st.markdown('<div class="sentinel-section-title">Rolling VaR</div>', unsafe_allow_html=True)
    if var_err:
        not_wired_notice(var_err)
    else:
        fig = build_rolling_line_chart(var_df["var"], name="VaR", color=COLORS.amber)
        st.plotly_chart(fig, use_container_width=True)

with es_col:
    st.markdown('<div class="sentinel-section-title">Rolling Expected Shortfall</div>', unsafe_allow_html=True)
    if es_err:
        not_wired_notice(es_err)
    else:
        fig = build_rolling_line_chart(es_df["expected_shortfall"], name="Expected Shortfall", color=COLORS.purple)
        st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# Volatility / Distribution
# ---------------------------------------------------------------------------
vol_col, dist_col = st.columns(2)

with vol_col:
    st.markdown('<div class="sentinel-section-title">Rolling Volatility</div>', unsafe_allow_html=True)
    if vol_err:
        not_wired_notice(vol_err)
    else:
        fig = build_rolling_line_chart(vol_series, name="Volatility", color=COLORS.blue)
        st.plotly_chart(fig, use_container_width=True)

with dist_col:
    st.markdown('<div class="sentinel-section-title">Return Distribution</div>', unsafe_allow_html=True)
    if price_err:
        not_wired_notice(price_err)
    else:
        returns = compute_returns(price_df)
        fig = build_distribution_histogram(returns)
        st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# Drawdown / Tail Losses
# ---------------------------------------------------------------------------
dd_col, tail_col = st.columns([2, 1])

with dd_col:
    st.markdown('<div class="sentinel-section-title">Drawdown</div>', unsafe_allow_html=True)
    if price_err:
        not_wired_notice(price_err)
    else:
        drawdown = compute_drawdown(price_df)
        fig = build_drawdown_chart(drawdown)
        st.plotly_chart(fig, use_container_width=True)

with tail_col:
    st.markdown('<div class="sentinel-section-title">Tail Losses</div>', unsafe_allow_html=True)
    if price_err:
        not_wired_notice(price_err)
    else:
        returns = compute_returns(price_df)
        tail_df = compute_tail_losses(returns, n=10)
        render_tail_losses_table(tail_df)
