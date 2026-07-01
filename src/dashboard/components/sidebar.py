"""
components/sidebar.py
======================
Left sidebar: asset selector, date range, VaR model selector, refresh
control. Returns the user's selections as a plain dataclass — pages read
from that, they don't touch st.session_state or widgets directly.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import streamlit as st

from config import ASSET_UNIVERSE, DEFAULT_ASSET, DEFAULT_LOOKBACK_DAYS, DEFAULT_MODEL, MODEL_OPTIONS


@dataclass(frozen=True)
class SidebarSelection:
    asset: str
    start_date: dt.date
    end_date: dt.date
    model: str
    refresh_requested: bool


def render_sidebar() -> SidebarSelection:
    with st.sidebar:
        st.markdown('<div class="sentinel-sidebar__section-label">Asset</div>', unsafe_allow_html=True)
        asset = st.selectbox(
            "Asset", ASSET_UNIVERSE, index=ASSET_UNIVERSE.index(DEFAULT_ASSET), label_visibility="collapsed"
        )

        st.markdown('<div class="sentinel-sidebar__section-label">Date Range</div>', unsafe_allow_html=True)
        default_end = dt.date.today()
        default_start = default_end - dt.timedelta(days=DEFAULT_LOOKBACK_DAYS)
        date_range = st.date_input(
            "Date Range",
            value=(default_start, default_end),
            max_value=default_end,
            label_visibility="collapsed",
        )
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_date, end_date = date_range
        else:
            start_date, end_date = default_start, default_end

        st.markdown('<div class="sentinel-sidebar__section-label">Model</div>', unsafe_allow_html=True)
        model = st.selectbox(
            "Model", MODEL_OPTIONS, index=MODEL_OPTIONS.index(DEFAULT_MODEL), label_visibility="collapsed"
        )

        st.markdown("<div style='margin-top: 18px;'></div>", unsafe_allow_html=True)
        refresh_requested = st.button("Refresh", use_container_width=True)

    return SidebarSelection(
        asset=asset,
        start_date=start_date,
        end_date=end_date,
        model=model,
        refresh_requested=refresh_requested,
    )
