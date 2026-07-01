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


def render_transition_matrix(matrix: pd.DataFrame) -> None:
    """Renders a from/to transition count matrix (Basel zones or market
    regimes) as a styled table."""
    st.dataframe(matrix, use_container_width=True)


def render_correlation_table(corr_matrix: pd.DataFrame) -> None:
    """Renders the correlation matrix as a plain numeric table,
    complementing the heatmap for exact values."""
    st.dataframe(corr_matrix.round(3), use_container_width=True)


def render_tail_losses_table(tail_df: pd.DataFrame) -> None:
    """Renders the worst-N single-day losses.

    Expects columns: date, return (the output of
    services.derived.compute_tail_losses).
    """
    display_df = tail_df.copy()
    display_df["date"] = pd.to_datetime(display_df["date"]).dt.strftime("%Y-%m-%d")
    display_df["return"] = display_df["return"].map(lambda x: f"{x:+.2%}")
    display_df = display_df.rename(columns={"date": "Date", "return": "Return"})
    st.dataframe(display_df, use_container_width=True, hide_index=True)


def render_explorer_table(df: pd.DataFrame, key_prefix: str = "explorer") -> pd.DataFrame:
    """
    Generic search + sort + filter + paginate table for the Database
    Explorer page. Operates purely on the DataFrame it's given — no
    querying. Returns the currently-visible page (useful if a caller
    wants to build the CSV export from exactly what's on screen, or the
    full filtered set — see the page for which one is exported).
    """
    search = st.text_input("Search", key=f"{key_prefix}_search", placeholder="Filter across all columns...")

    filtered = df
    if search:
        mask = df.astype(str).apply(lambda col: col.str.contains(search, case=False, na=False)).any(axis=1)
        filtered = df[mask]

    sort_col, page_col = st.columns([2, 1])
    with sort_col:
        sort_by = st.selectbox("Sort by", options=list(df.columns), key=f"{key_prefix}_sort")
    with page_col:
        page_size = st.selectbox("Rows per page", options=[25, 50, 100, 250], index=1, key=f"{key_prefix}_page_size")

    filtered = filtered.sort_values(by=sort_by, ascending=False)

    total_rows = len(filtered)
    total_pages = max(1, -(-total_rows // page_size))  # ceiling division
    page = st.number_input(
        "Page", min_value=1, max_value=total_pages, value=1, step=1, key=f"{key_prefix}_page"
    )

    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    page_df = filtered.iloc[start_idx:end_idx]

    st.caption(f"Showing {start_idx + 1}–{min(end_idx, total_rows)} of {total_rows} rows")
    st.dataframe(page_df, use_container_width=True, hide_index=True)

    st.download_button(
        "Export filtered results (CSV)",
        data=filtered.to_csv(index=False).encode("utf-8"),
        file_name="sentinel_export.csv",
        mime="text/csv",
        key=f"{key_prefix}_export",
    )

    return page_df
