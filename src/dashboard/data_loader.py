"""
data_loader.py
===============
THE ONLY module in this dashboard allowed to know that a backend exists.

Every page and component calls functions from this module — never a
repository, analytics function, or database session directly. This file
is intentionally the single seam between:

    PostgreSQL -> Repository Layer -> [ data_loader.py ] -> Streamlit UI

How to wire this up
--------------------
Each function below defines the CONTRACT the rest of the dashboard is
built against (exact return type + shape, documented in its docstring).
The body currently raises NotImplementedError with a one-line pointer to
what needs to be plugged in — no synthetic data, no placeholder charts,
nothing invented. Replace the `raise` with a call into your real
repository / analytics / validation modules, keeping the return
contract intact, and the entire dashboard lights up unchanged.

If a repository method you need doesn't exist yet, that's a signal to
extend the Repository layer — not to fake it here.
"""

from __future__ import annotations

import datetime as dt
from typing import Literal

import pandas as pd
import streamlit as st


# ---------------------------------------------------------------------------
# Connection / status
# ---------------------------------------------------------------------------
def database_is_connected() -> bool:
    """
    Returns True if a live DB session/engine can be established.

    Wire to: your session factory (e.g. src/repository/db.py or similar),
    typically `engine.connect()` inside a try/except, or a lightweight
    `SELECT 1`.
    """
    raise NotImplementedError(
        "database_is_connected(): wire to your SQLAlchemy engine/session factory."
    )


# ---------------------------------------------------------------------------
# Price history
# ---------------------------------------------------------------------------
@st.cache_data(ttl=300, show_spinner=False)
def get_price_history(symbol: str, start: dt.date, end: dt.date) -> pd.DataFrame:
    """
    Returns OHLCV price history for `symbol` between start/end (inclusive).

    Return contract:
        DataFrame indexed by `date` (DatetimeIndex), columns:
            open, high, low, close, volume   (all float64, volume may be int64)

    Wire to: src/repository/<market_data_repository>.get_price_series(...)
    or equivalent — the repository method that reads OHLCV rows from
    PostgreSQL for a single symbol.
    """
    raise NotImplementedError(
        "get_price_history(): wire to your Repository layer's price-history read."
    )


# ---------------------------------------------------------------------------
# Risk metrics
# ---------------------------------------------------------------------------
@st.cache_data(ttl=300, show_spinner=False)
def get_var(
    symbol: str,
    method: Literal["historical", "parametric"],
    start: dt.date,
    end: dt.date,
    confidence: float = 0.95,
) -> pd.DataFrame:
    """
    Returns the VaR time series already computed by src/analytics.

    Return contract:
        DataFrame indexed by `date`, columns:
            var            (float64, positive number = loss magnitude)
            price          (float64, close price that day, for overlay)
            breach         (bool, True if actual loss exceeded VaR that day)

    Wire to: src/analytics.<var_module>.historical_var(...) /
    parametric_var(...) via the Repository/Analytics service layer —
    the dashboard must NOT recompute VaR itself, only read the
    already-computed series.
    """
    raise NotImplementedError(
        f"get_var(method={method!r}): wire to src/analytics VaR output via the repository."
    )


@st.cache_data(ttl=300, show_spinner=False)
def get_expected_shortfall(
    symbol: str, start: dt.date, end: dt.date, confidence: float = 0.975
) -> pd.DataFrame:
    """
    Return contract:
        DataFrame indexed by `date`, columns:
            expected_shortfall   (float64)
            price                (float64)

    Wire to: src/analytics's Expected Shortfall output.
    """
    raise NotImplementedError(
        "get_expected_shortfall(): wire to src/analytics Expected Shortfall output."
    )


@st.cache_data(ttl=300, show_spinner=False)
def get_rolling_volatility(symbol: str, start: dt.date, end: dt.date, window: int = 21) -> pd.Series:
    """
    Return contract:
        Series indexed by `date`, name='volatility' (float64, annualized or
        raw per your analytics module's convention — label accordingly in UI).

    Wire to: src/analytics's rolling volatility function.
    """
    raise NotImplementedError("get_rolling_volatility(): wire to src/analytics rolling volatility output.")


@st.cache_data(ttl=300, show_spinner=False)
def get_correlation_matrix(symbols: list[str], start: dt.date, end: dt.date) -> pd.DataFrame:
    """
    Return contract:
        Square DataFrame, index and columns both = symbols, values = float64
        correlation coefficients in [-1, 1].

    Wire to: src/analytics's correlation output (already computed, not
    pandas .corr() run fresh here).
    """
    raise NotImplementedError("get_correlation_matrix(): wire to src/analytics correlation output.")


@st.cache_data(ttl=300, show_spinner=False)
def get_rolling_correlation(symbol_a: str, symbol_b: str, start: dt.date, end: dt.date, window: int = 63) -> pd.Series:
    """
    Return contract:
        Series indexed by `date`, name='correlation' (float64 in [-1, 1]).

    Wire to: src/analytics's rolling correlation output.
    """
    raise NotImplementedError("get_rolling_correlation(): wire to src/analytics rolling correlation output.")


@st.cache_data(ttl=300, show_spinner=False)
def get_beta(symbol: str, benchmark: str, start: dt.date, end: dt.date) -> float:
    """
    Return contract: single float64 beta value.

    Wire to: src/analytics's beta output.
    """
    raise NotImplementedError("get_beta(): wire to src/analytics beta output.")


@st.cache_data(ttl=300, show_spinner=False)
def get_risk_score(symbol: str, as_of: dt.date) -> dict:
    """
    Return contract:
        {
            "score": float,          # composite risk score, backend-defined scale
            "label": str,            # e.g. "Elevated", "Normal", "Severe"
            "components": dict,      # optional breakdown, backend-defined keys
        }

    Wire to: src/analytics's composite risk score output.
    """
    raise NotImplementedError("get_risk_score(): wire to src/analytics composite risk score output.")


# ---------------------------------------------------------------------------
# Market regime
# ---------------------------------------------------------------------------
@st.cache_data(ttl=300, show_spinner=False)
def get_market_regime(symbol: str, start: dt.date, end: dt.date) -> pd.DataFrame:
    """
    Return contract:
        DataFrame indexed by `date`, columns:
            regime   (str/category: e.g. "Bull", "Bear", "High Volatility", "Low Volatility")

    Wire to: src/analytics's regime detection output.
    """
    raise NotImplementedError("get_market_regime(): wire to src/analytics regime detection output.")


# ---------------------------------------------------------------------------
# Model validation
# ---------------------------------------------------------------------------
@st.cache_data(ttl=300, show_spinner=False)
def get_validation_summary(symbol: str, method: Literal["historical", "parametric"], as_of: dt.date) -> dict:
    """
    Return contract:
        {
            "kupiec":               {"statistic": float, "p_value": float, "result": "PASS" | "FAIL"},
            "christoffersen":       {"statistic": float, "p_value": float, "result": "PASS" | "FAIL"},
            "conditional_coverage": {"statistic": float, "p_value": float, "result": "PASS" | "FAIL"},
        }

    Wire to: src/validation's Kupiec / Christoffersen / Conditional
    Coverage test outputs.
    """
    raise NotImplementedError("get_validation_summary(): wire to src/validation test outputs.")


@st.cache_data(ttl=300, show_spinner=False)
def get_basel_traffic_light(symbol: str, method: Literal["historical", "parametric"], start: dt.date, end: dt.date) -> pd.DataFrame:
    """
    Return contract:
        DataFrame indexed by `date`, columns:
            zone              (str: "GREEN" | "YELLOW" | "RED")
            breach_count      (int, rolling breach count in the window)
            risk_multiplier   (float64, Basel scaling factor for that window)

    Wire to: src/validation's rolling Basel traffic-light output.
    """
    raise NotImplementedError("get_basel_traffic_light(): wire to src/validation Basel traffic-light output.")


# ---------------------------------------------------------------------------
# Recent events (Overview page "Recent Risk Events" panel)
# ---------------------------------------------------------------------------
@st.cache_data(ttl=300, show_spinner=False)
def get_recent_risk_events(symbol: str, limit: int = 10) -> pd.DataFrame:
    """
    Return contract:
        DataFrame, most recent first, columns:
            date         (datetime64)
            event_type   (str, e.g. "VaR Breach", "Regime Change", "Validation Failure")
            description  (str)
            severity     (str: "low" | "medium" | "high")

    Wire to: whichever repository/table logs breach + validation events.
    If none exists yet, this is the repository method that needs adding.
    """
    raise NotImplementedError("get_recent_risk_events(): wire to your risk-events repository/table.")
