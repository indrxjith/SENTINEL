"""
theme.py
========
Owns two things:

1. A registered Plotly template ("sentinel_dark") so every chart in the
   app looks identical without each chart module re-specifying fonts,
   gridlines, and colors.
2. A Streamlit CSS injector that loads assets/styles.css and hides the
   default Streamlit chrome (menu, footer, header branding).

Import `apply_theme()` once, at the top of app.py, before anything else
renders.
"""

from __future__ import annotations

from pathlib import Path

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

from config import COLORS, FONTS, GOOGLE_FONTS_URL

ASSETS_DIR = Path(__file__).parent / "assets"
SENTINEL_TEMPLATE_NAME = "sentinel_dark"


def _build_plotly_template() -> go.layout.Template:
    """Construct the shared Plotly template. Thin gridlines, muted axes,
    transparent backgrounds so charts sit flush inside our card components,
    and a hover label styled to match the rest of the terminal."""
    template = go.layout.Template()

    template.layout = go.Layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONTS.mono, color=COLORS.text_secondary, size=12),
        title=dict(font=dict(family=FONTS.body, color=COLORS.text_primary, size=14)),
        colorway=[COLORS.blue, COLORS.purple, COLORS.amber, COLORS.green, COLORS.red],
        xaxis=dict(
            gridcolor=COLORS.border,
            gridwidth=1,
            zeroline=False,
            linecolor=COLORS.border,
            tickfont=dict(family=FONTS.mono, color=COLORS.text_secondary, size=11),
            showspikes=True,
            spikecolor=COLORS.text_secondary,
            spikethickness=1,
            spikedash="dot",
        ),
        yaxis=dict(
            gridcolor=COLORS.border,
            gridwidth=1,
            zeroline=False,
            linecolor=COLORS.border,
            tickfont=dict(family=FONTS.mono, color=COLORS.text_secondary, size=11),
        ),
        legend=dict(
            font=dict(family=FONTS.body, color=COLORS.text_secondary, size=11),
            bgcolor="rgba(0,0,0,0)",
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
        hoverlabel=dict(
            bgcolor=COLORS.surface,
            bordercolor=COLORS.border,
            font=dict(family=FONTS.mono, color=COLORS.text_primary, size=12),
        ),
        margin=dict(l=48, r=24, t=32, b=32),
    )
    return template


def register_plotly_template() -> None:
    """Register + activate the SENTINEL Plotly template globally.
    Idempotent — safe to call on every rerun."""
    pio.templates[SENTINEL_TEMPLATE_NAME] = _build_plotly_template()
    pio.templates.default = SENTINEL_TEMPLATE_NAME


def _read_css() -> str:
    css_path = ASSETS_DIR / "styles.css"
    return css_path.read_text(encoding="utf-8") if css_path.exists() else ""


def apply_theme() -> None:
    """Inject fonts + stylesheet and strip Streamlit's default branding.
    Call once per page, immediately after st.set_page_config()."""
    register_plotly_template()

    st.markdown(
        f"""
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link href="{GOOGLE_FONTS_URL}" rel="stylesheet">
        <style>
        {_read_css()}
        </style>
        """,
        unsafe_allow_html=True,
    )
