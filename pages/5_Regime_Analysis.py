"""
pages/5_Regime_Analysis.py
=============================
Market regime timeline for the selected asset, plus a transition matrix
showing how often the market moved between regimes (Bull, Bear, High
Volatility, Low Volatility).

Regime labels come from data_loader.get_market_regime() — backend
regime-detection output. Collapsing per-day labels into contiguous
segments (for the timeline) and counting transitions are plain
post-processing, done in services/derived.py.
"""

from __future__ import annotations

import streamlit as st

import data_loader
from components.charts import build_regime_timeline
from components.navbar import render_navbar
from components.sidebar import render_sidebar
from components.status import not_wired_notice, safe_call
from components.tables import render_transition_matrix
from config import APP_TITLE
from services.derived import compute_regime_segments, compute_transition_matrix
from theme import apply_theme

st.set_page_config(page_title=f"{APP_TITLE} — Market Regimes", layout="wide", initial_sidebar_state="expanded")
apply_theme()

selection = render_sidebar()
db_status, _ = safe_call(data_loader.database_is_connected)
render_navbar(selected_asset=selection.asset, db_connected=db_status)

regime_df, regime_err = safe_call(
    data_loader.get_market_regime, selection.asset, selection.start_date, selection.end_date
)

st.markdown('<div class="sentinel-section-title">Regime Timeline</div>', unsafe_allow_html=True)
if regime_err:
    not_wired_notice(regime_err)
else:
    segments = compute_regime_segments(regime_df)
    fig = build_regime_timeline(segments)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="sentinel-section-title">Regime Transitions</div>', unsafe_allow_html=True)
    transition_matrix = compute_transition_matrix(regime_df["regime"])
    render_transition_matrix(transition_matrix)

    current_regime = regime_df["regime"].iloc[-1]
    days_in_regime = int((regime_df["regime"] == current_regime)[::-1].cumprod().sum())
    st.markdown(
        f"""
        <div class="sentinel-card" style="margin-top: 12px;">
            <div class="sentinel-card__label">Current Regime</div>
            <div class="sentinel-card__value">{current_regime}</div>
            <div class="sentinel-card__delta">{days_in_regime} trading days in this regime</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
