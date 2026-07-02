"""
app.py
======
SENTINEL entry point.

Streamlit automatically discovers all pages inside the `pages/`
directory. This file only configures the application and applies the
global theme.
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
