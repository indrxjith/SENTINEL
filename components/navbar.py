"""
components/navbar.py
=====================
Top navigation bar: brand, live clock, DB connection status, selected
asset. Pure presentation — takes its inputs as arguments, never calls
data_loader directly, so it can be unit-tested/rendered without a live DB.
"""

from __future__ import annotations

import datetime as dt

import streamlit as st

from config import APP_SUBTITLE, APP_TITLE


def render_navbar(selected_asset: str, db_connected: bool | None) -> None:
    """
    Renders the SENTINEL top bar.

    Parameters
    ----------
    selected_asset : the currently selected symbol, e.g. "SPY"
    db_connected : True/False once data_loader.database_is_connected() is
        wired; pass None while that function still raises NotImplementedError
        so the bar shows an honest "Not Configured" state instead of a
        fake green dot.
    """
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if db_connected is None:
        status_dot, status_text = "status-dot--disconnected", "NOT CONFIGURED"
    elif db_connected:
        status_dot, status_text = "status-dot--connected", "CONNECTED"
    else:
        status_dot, status_text = "status-dot--disconnected", "DISCONNECTED"

    st.markdown(
        f"""
        <div class="sentinel-navbar">
            <div class="sentinel-navbar__brand">
                <span class="sentinel-navbar__title">{APP_TITLE}</span>
                <span class="sentinel-navbar__subtitle">{APP_SUBTITLE}</span>
            </div>
            <div class="sentinel-navbar__status">
                <div class="sentinel-navbar__status-item">
                    <span class="status-dot {status_dot}"></span>
                    <span>DB: {status_text}</span>
                </div>
                <div class="sentinel-navbar__status-item">
                    <span>ASSET: {selected_asset}</span>
                </div>
                <div class="sentinel-navbar__status-item mono">
                    <span>{now}</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
