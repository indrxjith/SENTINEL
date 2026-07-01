"""
components/tables.py
=====================
Dark-themed table renderers. Takes DataFrames already shaped by
data_loader / pages — no querying here.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st


def render_events_table(events_df: pd.DataFrame) -> None:
    """
    Renders the 'Recent Risk Events' panel.

    Expects the contract from data_loader.get_recent_risk_events():
    columns = date, event_type, description, severity.
    """
    if events_df.empty:
        st.markdown(
            '<div class="sentinel-card" style="text-align:center; color: var(--text-secondary);">'
            "No recent risk events." "</div>",
            unsafe_allow_html=True,
        )
        return

    display_df = events_df.copy()
    display_df["date"] = pd.to_datetime(display_df["date"]).dt.strftime("%Y-%m-%d %H:%M")
    display_df = display_df.rename(
        columns={"date": "Date", "event_type": "Event", "description": "Description", "severity": "Severity"}
    )
    st.dataframe(display_df, use_container_width=True, hide_index=True)


def render_validation_table(validation_summary: dict) -> None:
    """
    Renders the Kupiec / Christoffersen / Conditional Coverage results as
    a clean statistical table.

    Expects the contract from data_loader.get_validation_summary().
    """
    rows = []
    for test_name, result in validation_summary.items():
        rows.append(
            {
                "Test": test_name.replace("_", " ").title(),
                "Statistic": f"{result['statistic']:.4f}",
                "P-Value": f"{result['p_value']:.4f}",
                "Result": result["result"],
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
