"""
pages/3_Model_Validation.py
=============================
Risk-committee-style validation report: Kupiec, Christoffersen, and
Conditional Coverage test results as large status cards; Basel rolling
traffic light with transition matrix, conditional breach probability,
current risk multiplier, and worst window on record.

Test results and the Basel zone/multiplier series come straight from
data_loader (backend-computed). The transition matrix, conditional
breach probability, and worst-window lookup are plain counting/sorting
over that already-computed series — see services/derived.py.
"""

from __future__ import annotations

import streamlit as st

import data_loader
from components.cards import render_status_badge
from components.navbar import render_navbar
from components.sidebar import render_sidebar
from components.status import not_wired_notice, safe_call
from components.tables import render_transition_matrix, render_validation_table
from config import APP_TITLE
from services.derived import (
    compute_conditional_breach_probability,
    compute_transition_matrix,
    find_worst_basel_window,
)
from theme import apply_theme

st.set_page_config(
    page_title=f"{APP_TITLE} — Model Validation",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_theme()

selection = render_sidebar()
db_status, _ = safe_call(data_loader.database_is_connected)
render_navbar(selected_asset=selection.asset, db_connected=db_status)

method_key = selection.model.lower().replace(" ", "_")
if method_key not in ("historical", "parametric"):
    method_key = "historical"

# ---------------------------------------------------------------------------
# Statistical test status cards
# ---------------------------------------------------------------------------
st.markdown(
    '<div class="sentinel-section-title">Statistical Test Results</div>',
    unsafe_allow_html=True,
)

validation_summary, validation_err = safe_call(
    data_loader.get_validation_summary,
    selection.asset,
    method_key,
    selection.end_date,
)

if validation_err:
    not_wired_notice(validation_err)
else:
    test_labels = {
        "kupiec": "Kupiec Test",
        "christoffersen": "Christoffersen Independence",
        "conditional_coverage": "Conditional Coverage",
    }

    cols = st.columns(len(validation_summary))

    for col, (test_key, result) in zip(cols, validation_summary.items()):
        with col:
            variant = "pass" if result["result"] == "PASS" else "fail"

            st.markdown(
                f"""
                <div class="sentinel-card">
                    <div class="sentinel-card__label">
                        {test_labels.get(test_key, test_key.title())}
                    </div>
                    <div class="sentinel-card__value">
                        {result['statistic']:.4f}
                    </div>
                    <div class="sentinel-card__delta" style="margin-top:8px;">
                        p-value: {result['p_value']:.4f}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            render_status_badge(result["result"], variant)

    st.markdown("<div style='margin-top:12px;'></div>", unsafe_allow_html=True)

    render_validation_table(validation_summary)

# ---------------------------------------------------------------------------
# Basel Rolling Traffic Light
# ---------------------------------------------------------------------------
st.markdown(
    '<div class="sentinel-section-title">Basel Rolling Traffic Light</div>',
    unsafe_allow_html=True,
)

basel_df, basel_err = safe_call(
    data_loader.get_basel_traffic_light,
    selection.asset,
    method_key,
    selection.start_date,
    selection.end_date,
)

if basel_err:
    not_wired_notice(basel_err)
else:
    latest = basel_df.iloc[-1]

    zone_variant = {
        "GREEN": "green",
        "YELLOW": "amber",
        "RED": "red",
    }.get(latest["zone"], "amber")

    kpi_cols = st.columns(4)

    with kpi_cols[0]:
        st.markdown(
            '<div class="sentinel-card__label">Current Zone</div>',
            unsafe_allow_html=True,
        )
        render_status_badge(latest["zone"], zone_variant)

    with kpi_cols[1]:
        st.markdown(
            f"""
            <div class="sentinel-card">
                <div class="sentinel-card__label">Risk Multiplier</div>
                <div class="sentinel-card__value">
                    {latest['risk_multiplier']:.2f}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with kpi_cols[2]:
        breach_window = (
            int(basel_df["breach_count"].iloc[-1])
            if "breach_count" in basel_df
            else 0
        )

        conditional_prob = compute_conditional_breach_probability(
            basel_df,
            window=max(breach_window, 1),
        )

        st.markdown(
            f"""
            <div class="sentinel-card">
                <div class="sentinel-card__label">
                    Conditional Breach Probability
                </div>
                <div class="sentinel-card__value">
                    {conditional_prob:.2%}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with kpi_cols[3]:
        worst = find_worst_basel_window(basel_df)

        st.markdown(
            f"""
            <div class="sentinel-card">
                <div class="sentinel-card__label">
                    Worst Basel Window
                </div>
                <div class="sentinel-card__value">
                    {worst.get('zone', '—')}
                </div>
                <div class="sentinel-card__delta">
                    {worst.get('date', '')}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        '<div class="sentinel-section-title">Zone Transition Matrix</div>',
        unsafe_allow_html=True,
    )

    transition_matrix = compute_transition_matrix(basel_df["zone"])
    render_transition_matrix(transition_matrix)

    st.markdown(
        '<div class="sentinel-section-title">Interpretation</div>',
        unsafe_allow_html=True,
    )

    if latest["zone"] == "RED":
        interpretation = (
            "The model is currently in the RED zone under the Basel framework. "
            "Breach frequency exceeds acceptable bounds — this typically triggers "
            "a mandated capital multiplier increase and model recalibration review."
        )
    elif latest["zone"] == "YELLOW":
        interpretation = (
            "The model is in the YELLOW zone. Breach frequency is elevated but not "
            "yet at a level requiring automatic escalation — increased monitoring is warranted."
        )
    else:
        interpretation = (
            "The model is in the GREEN zone. Breach frequency is within expected "
            "statistical bounds."
        )

    st.markdown(
        f'<div class="sentinel-card">{interpretation}</div>',
        unsafe_allow_html=True,
    )