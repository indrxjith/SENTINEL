"""
components/status.py
=====================
Shared helper used by every page to call data_loader functions without
a missing backend wire crashing the whole page. Centralized here so all
six pages report "not wired" the same way instead of each reimplementing
the try/except.
"""

from __future__ import annotations

from typing import Any, Callable, TypeVar

import streamlit as st

T = TypeVar("T")


def safe_call(fn: Callable[..., T], *args: Any, **kwargs: Any) -> tuple[T | None, str | None]:
    """
    Calls a data_loader function and returns (result, error_message).

    Isolates NotImplementedError (backend not wired yet) and any other
    exception the backend call might raise, so one missing/broken piece
    of the backend doesn't take down the whole page — each section
    reports its own status instead.
    """
    try:
        return fn(*args, **kwargs), None
    except NotImplementedError as exc:
        return None, str(exc)
    except Exception as exc:  # noqa: BLE001 — surfacing real backend errors to the UI is intentional here
        return None, f"Backend error: {exc}"


def not_wired_notice(message: str) -> None:
    """Renders the standard amber 'Backend Not Wired' card in place of
    a chart/table/metric whose data_loader call isn't wired yet."""
    st.markdown(
        f"""
        <div class="sentinel-card" style="border-color: rgba(255,179,0,0.3);">
            <div class="sentinel-card__label" style="color: var(--amber);">Backend Not Wired</div>
            <div style="color: var(--text-secondary); font-size: 13px; font-family: var(--font-mono);">{message}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
