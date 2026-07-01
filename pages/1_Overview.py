"""
pages/1_Overview.py
====================
SENTINEL's landing page: top KPI row, main price/risk chart, recent
risk events, and latest validation summary.

Every value on this page comes from data_loader.py. Nothing is computed
here. Until data_loader's functions are wired to the real Repository /
Analytics / Validation layers, each section shows an explicit
"Backend not wired" notice instead of any placeholder or synthetic
number — see the NotImplementedError bodies in data_loader.py for the
exact call each section is waiting on.
"""

from __future__ import annotations

import streamlit as st

import data_loader
from components.cards import render_kpi_row
from components.charts import build_price_risk_chart
from components.gauges import build_risk_score_gauge
from components.navbar import render_navbar
from components.sidebar import render_sidebar
from components.status import not_wired_notice, safe_call
from components.tables import render_events_table, render_validation_table
from config import APP_TITLE
from theme import apply_theme

st.set_page_config(page_title=f"{APP_TITLE} — Overview", layout="wide", initial_sidebar_state="expanded")
apply_theme()

_safe = safe_call
_not_wired_notice = not_wired_notice


# ---------------------------------------------------------------------------
# Sidebar + navbar
# ---------------------------------------------------------------------------
selection = render_sidebar()

db_status, _ = _safe(data_loader.database_is_connected)
render_navbar(selected_asset=selection.asset, db_connected=db_status)

method_key = selection.model.lower().replace(" ", "_")
if method_key not in ("historical", "parametric"):
    method_key = "historical"  # Expected Shortfall model selection reuses the ES-specific call below

# ---------------------------------------------------------------------------
# KPI row
# ---------------------------------------------------------------------------
price_df, price_err = _safe(data_loader.get_price_history, selection.asset, selection.start_date, selection.end_date)
var_df, var_err = _safe(data_loader.get_var, selection.asset, method_key, selection.start_date, selection.end_date)
es_df, es_err = _safe(data_loader.get_expected_shortfall, selection.asset, selection.start_date, selection.end_date)
risk_score, risk_err = _safe(data_loader.get_risk_score, selection.asset, selection.end_date)
regime_df, regime_err = _safe(data_loader.get_market_regime, selection.asset, selection.start_date, selection.end_date)

st.markdown('<div class="sentinel-section-title">Key Risk Indicators</div>', unsafe_allow_html=True)

any_kpi_error = any([price_err, var_err, es_err, risk_err, regime_err])
if any_kpi_error:
    _not_wired_notice(
        next(e for e in [price_err, var_err, es_err, risk_err, regime_err] if e)
    )
else:
    latest_price = price_df["close"].iloc[-1]
    prior_price = price_df["close"].iloc[-2]
    daily_return = (latest_price / prior_price) - 1
    latest_var = var_df["var"].iloc[-1]
    latest_es = es_df["expected_shortfall"].iloc[-1]
    latest_regime = regime_df["regime"].iloc[-1]

    render_kpi_row([
        {"label": "Current Price", "value": f"{latest_price:,.2f}"},
        {
            "label": "Daily Return",
            "value": f"{daily_return * 100:+.2f}%",
            "delta_direction": "up" if daily_return >= 0 else "down",
        },
        {"label": "Historical VaR", "value": f"{latest_var:,.2f}"},
        {"label": "Expected Shortfall", "value": f"{latest_es:,.2f}"},
        {"label": "Risk Score", "value": f"{risk_score['score']:.1f}", "delta": risk_score["label"]},
        {"label": "Market Regime", "value": latest_regime},
    ])

# ---------------------------------------------------------------------------
# Main chart + risk score gauge
# ---------------------------------------------------------------------------
st.markdown('<div class="sentinel-section-title">Price &amp; Risk Overlay</div>', unsafe_allow_html=True)

chart_col, gauge_col = st.columns([3, 1])
with chart_col:
    if price_err or var_err:
        _not_wired_notice(price_err or var_err)
    else:
        fig = build_price_risk_chart(price_df, var_df, es_df if not es_err else None)
        st.plotly_chart(fig, use_container_width=True)

with gauge_col:
    if risk_err:
        _not_wired_notice(risk_err)
    else:
        gauge = build_risk_score_gauge(risk_score["score"], label="Composite Risk Score")
        st.plotly_chart(gauge, use_container_width=True)

# ---------------------------------------------------------------------------
# Recent events + validation summary
# ---------------------------------------------------------------------------
events_col, validation_col = st.columns(2)

with events_col:
    st.markdown('<div class="sentinel-section-title">Recent Risk Events</div>', unsafe_allow_html=True)
    events_df, events_err = _safe(data_loader.get_recent_risk_events, selection.asset)
    if events_err:
        _not_wired_notice(events_err)
    else:
        render_events_table(events_df)

with validation_col:
    st.markdown('<div class="sentinel-section-title">Latest Model Validation</div>', unsafe_allow_html=True)
    validation_summary, validation_err = _safe(
        data_loader.get_validation_summary, selection.asset, method_key, selection.end_date
    )
    if validation_err:
        _not_wired_notice(validation_err)
    else:
        render_validation_table(validation_summary)
