"""
app.py
======
SENTINEL entry point. Streamlit's native multipage routing (the
`pages/` directory) drives navigation — this file only configures the
page and lands the user on Overview by default.

Each page under pages/ is self-contained: it calls apply_theme(),
renders the navbar/sidebar, and pulls data exclusively through
data_loader.py.
"""

from __future__ import annotations

import streamlit as st

from config import APP_TITLE
from theme import apply_theme

st.set_page_config(
    page_title=f"{APP_TITLE} — Market Risk Intelligence",
    page_icon="assets/logo.svg",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_theme()

st.switch_page("pages/1_Overview.py")
