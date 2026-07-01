"""
components/cards.py
====================
KPI cards for the Overview row and status badges (PASS/FAIL, Basel traffic
light) used on the Model Validation page. All functions take already-
computed values as arguments — no data fetching here.
"""

from __future__ import annotations

from typing import Literal

import streamlit as st


def render_kpi_card(
    label: str,
    value: str,
    delta: str | None = None,
    delta_direction: Literal["up", "down", "flat"] = "flat",
) -> None:
    """
    Renders a single dense KPI card.

    `value` is pre-formatted by the caller (e.g. "$482.13", "-1.24%",
    "2.8σ") — this component does no number formatting, since formatting
    conventions (currency, precision, sign) belong to the page/service
    that knows what the number means.
    """
    delta_html = ""
    if delta is not None:
        delta_html = f'<div class="sentinel-card__delta sentinel-card__delta--{delta_direction}">{delta}</div>'

    st.markdown(
        f"""
        <div class="sentinel-card">
            <div class="sentinel-card__label">{label}</div>
            <div class="sentinel-card__value">{value}</div>
            {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpi_row(cards: list[dict]) -> None:
    """
    Renders a row of KPI cards evenly spaced.

    `cards` is a list of dicts with keys: label, value, delta (optional),
    delta_direction (optional).
    """
    cols = st.columns(len(cards))
    for col, card in zip(cols, cards):
        with col:
            render_kpi_card(
                label=card["label"],
                value=card["value"],
                delta=card.get("delta"),
                delta_direction=card.get("delta_direction", "flat"),
            )


def render_badge(text: str, variant: Literal["pass", "fail", "green", "amber", "red", "yellow"]) -> str:
    """Returns the badge HTML (caller embeds it inside a larger st.markdown
    block, e.g. a validation report row) rather than rendering directly —
    keeps this composable inside tables."""
    return f'<span class="sentinel-badge sentinel-badge--{variant}">{text}</span>'


def render_status_badge(text: str, variant: Literal["pass", "fail", "green", "amber", "red", "yellow"]) -> None:
    """Standalone badge render, for placing directly in the layout."""
    st.markdown(render_badge(text, variant), unsafe_allow_html=True)
