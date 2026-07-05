"""
data_loader.py

Single bridge between the SENTINEL Streamlit dashboard and the real
backend (PostgreSQL repositories + src/analytics). Every page imports
ONLY from this module -- no page ever touches a Repository or an
analytics engine directly, and no page ever recomputes a risk metric
that belongs in src/analytics.

Contract notes (read before changing a return shape)
-----------------------------------------------------
Every function below is called through components.status.safe_call(),
which catches whatever it raises and shows an amber "Backend Not
Wired" card instead of crashing the page. That means:
    - Raise NotImplementedError("...") for anything genuinely not
      wired yet, with a message describing what needs connecting.
    - Let real repository/analytics exceptions propagate -- safe_call
      turns them into a visible "Backend error: ..." card, which is
      more useful to an analyst than a silent empty chart.

Shapes each page/component depends on (do not change without also
updating the corresponding component in components/ and services/derived.py):
    get_price_history        -> DataFrame indexed by trade_date, has "close"
    get_var                  -> DataFrame indexed by trade_date, has "var", "price", "breach"
    get_expected_shortfall    -> DataFrame indexed by trade_date, has "expected_shortfall", "price"
    get_rolling_volatility    -> Series indexed by trade_date, name "volatility"
    get_risk_score            -> dict {"score": float, "label": str}
    get_market_regime         -> DataFrame indexed by trade_date, has "regime"
    get_recent_risk_events    -> DataFrame with columns date, event_type, description, severity
    get_correlation_matrix    -> square DataFrame, index/columns = symbols
    get_rolling_correlation   -> Series indexed by trade_date, name "correlation"
    get_validation_summary    -> dict of dicts: {test_key: {"result": "PASS"/"FAIL"/"N/A", "statistic": float, "p_value": float}}
    get_basel_traffic_light   -> DataFrame indexed by trade_date, has "zone" ("GREEN"/"YELLOW"/"RED"), "risk_multiplier", "breach_count"
    get_market_data_table     -> flat DataFrame (not indexed), raw rows for the Database Explorer
"""

from __future__ import annotations

import datetime as dt
from typing import Literal

import pandas as pd
import streamlit as st
from sqlalchemy import text

from config import ASSET_SYMBOL_MAP, DISPLAY_SYMBOL_MAP, VAR_CONFIDENCE
from src.analytics.model_validation import ModelValidation
from src.repository.beta_repository import BetaRepository
from src.repository.correlation_repository import CorrelationRepository
from src.repository.expected_shortfall_repository import ExpectedShortfallRepository
from src.repository.feature_repository import FeatureRepository
from src.repository.market_repository import MarketRepository
from src.repository.regime_repository import RegimeRepository
from src.repository.risk_score_repository import RiskScoreRepository
from src.repository.var_repository import VarRepository
from src.utils.database import engine

# Basel's traffic-light framework is only rigorously defined at the 99%
# confidence level over a 250-observation window -- see
# src/analytics/model_validation.py's basel_traffic_light docstring.
_BASEL_CONFIDENCE_SUFFIX = "99"
_BASEL_WINDOW = 250


# ==========================================================
# DATABASE
# ==========================================================

def database_is_connected() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


# ==========================================================
# Internal helpers
# ==========================================================

def _raw_symbol(symbol: str) -> str:
    """UI display symbol (e.g. 'BTC') -> the raw ticker string every
    repository actually stores (e.g. 'BTC-USD'). No-op for symbols that
    are already identical in both forms (SPY, QQQ, GLD, USO)."""
    return ASSET_SYMBOL_MAP.get(symbol, symbol)


def _display_symbol(symbol: str) -> str:
    """Raw ticker string from a repository row (e.g. '^VIX') -> the UI's
    clean display symbol (e.g. 'VIX'). No-op for anything not in the map."""
    return DISPLAY_SYMBOL_MAP.get(symbol, symbol)


def _filter_date_range(df: pd.DataFrame, date_col: str, start: dt.date, end: dt.date) -> pd.DataFrame:
    return df[(df[date_col] >= pd.Timestamp(start)) & (df[date_col] <= pd.Timestamp(end))]


def _nearest_window_column(window: int, prefix: str, available: tuple = (20, 60, 252), suffix: str = "") -> str:
    """
    Picks the precomputed rolling-window column closest to the
    requested window. The backend only ever materializes a fixed set
    of windows (20/60/252 day), while the UI slider is continuous --
    this maps any slider value to the nearest one actually available,
    rather than a brittle tiered if/elif that silently mishandles
    values between the tiers.

    `suffix` accounts for the schema's inconsistent naming between
    tables: market_features uses "annualized_volatility_20d" (day
    suffix) while asset_correlations uses "rolling_corr_20" (no
    suffix) for the same kind of window.
    """
    closest = min(available, key=lambda w: abs(w - window))
    return f"{prefix}_{closest}{suffix}"


def _load_var_breach_series(
    symbol: str,
    method_key: str,
    confidence_suffix: str,
) -> pd.DataFrame:
    """
    Merges returns (FeatureRepository) with the requested VaR column
    (VarRepository) and computes a breach flag. Shared by
    get_validation_summary and get_basel_traffic_light, which both
    need a hit sequence rather than a chart-ready frame.

    Returns a DataFrame indexed by trade_date with columns:
        simple_return, var_value (the raw, signed VaR figure), breach
    """
    raw = _raw_symbol(symbol)
    features = FeatureRepository().fetch_symbol(raw)
    var = VarRepository().fetch_symbol(raw)

    if features.empty or var.empty:
        raise NotImplementedError(
            f"No feature/VaR data available for {symbol!r} yet -- "
            f"run the feature and VaR pipelines for this symbol."
        )

    features["trade_date"] = pd.to_datetime(features["trade_date"])
    var["trade_date"] = pd.to_datetime(var["trade_date"])

    var_col = f"{method_key}_var_{confidence_suffix}"
    if var_col not in var.columns:
        raise NotImplementedError(
            f"Column {var_col!r} not found in asset_var -- check that "
            f"the {method_key} VaR pipeline has been run."
        )

    df = features[["trade_date", "simple_return"]].merge(
        var[["trade_date", var_col]],
        on="trade_date",
        how="inner",
    )
    df = df.sort_values("trade_date").reset_index(drop=True)

    df["breach"] = df["simple_return"] < df[var_col]
    df = df.rename(columns={var_col: "var_value"})

    return df.set_index("trade_date")


# ==========================================================
# PRICE HISTORY
# ==========================================================

@st.cache_data(ttl=300, show_spinner=False)
def get_price_history(
    symbol: str,
    start: dt.date,
    end: dt.date,
) -> pd.DataFrame:

    df = MarketRepository().fetch_symbol(_raw_symbol(symbol))

    if df.empty:
        raise NotImplementedError(
            f"No market price data available for {symbol!r} yet -- "
            f"run the market data pipeline for this symbol."
        )

    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df = _filter_date_range(df, "trade_date", start, end)

    return df.set_index("trade_date")


# ==========================================================
# VALUE AT RISK
# ==========================================================

@st.cache_data(ttl=300, show_spinner=False)
def get_var(
    symbol: str,
    method: str,
    start: dt.date,
    end: dt.date,
    confidence: float = VAR_CONFIDENCE,
) -> pd.DataFrame:

    raw = _raw_symbol(symbol)
    prices = MarketRepository().fetch_symbol(raw)
    var = VarRepository().fetch_symbol(raw)

    if prices.empty or var.empty:
        raise NotImplementedError(
            f"No price/VaR data available for {symbol!r} yet -- "
            f"run the market data and VaR pipelines for this symbol."
        )

    prices["trade_date"] = pd.to_datetime(prices["trade_date"])
    var["trade_date"] = pd.to_datetime(var["trade_date"])

    suffix = "99" if confidence >= 0.99 else "95"
    column = f"{method}_var_{suffix}"
    if column not in var.columns:
        raise NotImplementedError(
            f"Column {column!r} not found in asset_var -- check that "
            f"the {method} VaR pipeline has been run."
        )

    df = prices.merge(var[["trade_date", column]], on="trade_date", how="inner")
    df = _filter_date_range(df, "trade_date", start, end)
    df = df.sort_values("trade_date").reset_index(drop=True)

    # Stored VaR figures are signed returns (e.g. -0.032 for a 3.2%
    # loss threshold); "var" here is the same signed value so it plots
    # directly under the return series it's being compared to.
    df["var"] = df[column]

    returns = df["close"].pct_change()
    df["breach"] = returns < df["var"]

    df = df.set_index("trade_date")

    return df[["var", "close", "breach"]].rename(columns={"close": "price"})


# ==========================================================
# EXPECTED SHORTFALL
# ==========================================================

@st.cache_data(ttl=300, show_spinner=False)
def get_expected_shortfall(
    symbol: str,
    start: dt.date,
    end: dt.date,
    confidence: float = 0.975,
) -> pd.DataFrame:

    raw = _raw_symbol(symbol)
    prices = MarketRepository().fetch_symbol(raw)
    es = ExpectedShortfallRepository().fetch_symbol(raw)

    if prices.empty or es.empty:
        raise NotImplementedError(
            f"No price/Expected Shortfall data available for {symbol!r} "
            f"yet -- run the market data and Expected Shortfall pipelines "
            f"for this symbol."
        )

    prices["trade_date"] = pd.to_datetime(prices["trade_date"])
    es["trade_date"] = pd.to_datetime(es["trade_date"])

    # Only expected_shortfall_95 / expected_shortfall_99 are materialized;
    # 97.5% (the regulatory FRTB default) is paired with the 95% figure,
    # which is the tail it is computed beyond.
    column = "expected_shortfall_99" if confidence >= 0.99 else "expected_shortfall_95"
    if column not in es.columns:
        raise NotImplementedError(
            f"Column {column!r} not found in asset_expected_shortfall -- "
            f"check that the Expected Shortfall pipeline has been run."
        )

    df = prices.merge(es[["trade_date", column]], on="trade_date", how="inner")
    df = _filter_date_range(df, "trade_date", start, end)
    df = df.sort_values("trade_date").reset_index(drop=True)
    df = df.set_index("trade_date")

    return df[[column, "close"]].rename(
        columns={column: "expected_shortfall", "close": "price"}
    )


# ==========================================================
# ROLLING VOLATILITY
# ==========================================================

@st.cache_data(ttl=300, show_spinner=False)
def get_rolling_volatility(
    symbol: str,
    start: dt.date,
    end: dt.date,
    window: int = 20,
) -> pd.Series:

    df = FeatureRepository().fetch_symbol(_raw_symbol(symbol))

    if df.empty:
        raise NotImplementedError(
            f"No feature data available for {symbol!r} yet -- "
            f"run the feature pipeline for this symbol."
        )

    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df = _filter_date_range(df, "trade_date", start, end)
    df = df.sort_values("trade_date")

    column = _nearest_window_column(window, "annualized_volatility", suffix="d")
    if column not in df.columns:
        raise NotImplementedError(
            f"Column {column!r} not found in market_features -- check "
            f"that the feature pipeline has been run."
        )

    return pd.Series(
        df[column].values,
        index=pd.DatetimeIndex(df["trade_date"], name="trade_date"),
        name="volatility",
    )


# ==========================================================
# BETA
# ==========================================================

@st.cache_data(ttl=300, show_spinner=False)
def get_beta(
    symbol: str,
    benchmark: str = "SPY",
) -> float:

    df = BetaRepository().fetch_symbol(_raw_symbol(symbol))

    if df.empty:
        raise NotImplementedError(
            f"No beta data available for {symbol!r} yet -- "
            f"run the beta pipeline for this symbol."
        )

    df = df[df["benchmark"] == _raw_symbol(benchmark)]
    if df.empty:
        raise NotImplementedError(
            f"No beta data for {symbol!r} against benchmark "
            f"{benchmark!r} -- check the beta pipeline's benchmark list."
        )

    return float(df.sort_values("trade_date").iloc[-1]["beta_252"])


# ==========================================================
# RISK SCORE
# ==========================================================

@st.cache_data(ttl=300, show_spinner=False)
def get_risk_score(
    symbol: str,
    as_of: dt.date,
) -> dict:

    df = RiskScoreRepository().fetch_symbol(_raw_symbol(symbol))

    if df.empty:
        raise NotImplementedError(
            f"No risk score data available for {symbol!r} yet -- "
            f"run the risk score pipeline for this symbol."
        )

    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df = df[df["trade_date"] <= pd.Timestamp(as_of)].sort_values("trade_date")

    if df.empty:
        raise NotImplementedError(
            f"No risk score data for {symbol!r} on or before {as_of} -- "
            f"try a later date."
        )

    latest = df.iloc[-1]

    return {
        "score": float(latest["total_score"]),
        "label": latest["risk_level"],
        "components": {
            "volatility": float(latest["volatility_score"]),
            "drawdown": float(latest["drawdown_score"]),
            "beta": float(latest["beta_score"]),
            "var": float(latest["var_score"]),
            "expected_shortfall": float(latest["expected_shortfall_score"]),
        },
    }


# ==========================================================
# CORRELATION MATRIX
# ==========================================================

@st.cache_data(ttl=300, show_spinner=False)
def get_correlation_matrix(
    symbols: list,
    start: dt.date,
    end: dt.date,
) -> pd.DataFrame:

    df = CorrelationRepository().fetch_all()

    if df.empty:
        raise NotImplementedError(
            "No correlation data available yet -- run the correlation "
            "pipeline."
        )

    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df = _filter_date_range(df, "trade_date", start, end)

    if df.empty:
        raise NotImplementedError(
            f"No correlation data in range {start}-{end} -- "
            f"widen the date range."
        )

    latest_date = df["trade_date"].max()
    df = df[df["trade_date"] == latest_date]

    matrix = pd.DataFrame(index=symbols, columns=symbols, dtype=float)
    for s in symbols:
        matrix.loc[s, s] = 1.0

    for _, row in df.iterrows():
        a, b = _display_symbol(row["asset_1"]), _display_symbol(row["asset_2"])
        if a not in matrix.index or b not in matrix.columns:
            continue
        value = row["rolling_corr_60"]
        matrix.loc[a, b] = value
        matrix.loc[b, a] = value

    return matrix.fillna(0.0)


# ==========================================================
# ROLLING CORRELATION
# ==========================================================

@st.cache_data(ttl=300, show_spinner=False)
def get_rolling_correlation(
    symbol_a: str,
    symbol_b: str,
    start: dt.date,
    end: dt.date,
    window: int = 60,
) -> pd.Series:

    df = CorrelationRepository().fetch_all()

    if df.empty:
        raise NotImplementedError(
            "No correlation data available yet -- run the correlation "
            "pipeline."
        )

    raw_a, raw_b = _raw_symbol(symbol_a), _raw_symbol(symbol_b)
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df = df[
        ((df.asset_1 == raw_a) & (df.asset_2 == raw_b))
        | ((df.asset_1 == raw_b) & (df.asset_2 == raw_a))
    ]
    df = _filter_date_range(df, "trade_date", start, end)
    df = df.sort_values("trade_date")

    if df.empty:
        raise NotImplementedError(
            f"No correlation data for {symbol_a}/{symbol_b} in range "
            f"{start}-{end}."
        )

    column = _nearest_window_column(window, "rolling_corr")
    if column not in df.columns:
        raise NotImplementedError(
            f"Column {column!r} not found in asset_correlations."
        )

    return pd.Series(
        df[column].values,
        index=pd.DatetimeIndex(df["trade_date"], name="trade_date"),
        name="correlation",
    )


# ==========================================================
# MARKET REGIME
# ==========================================================

@st.cache_data(ttl=300, show_spinner=False)
def get_market_regime(
    symbol: str,
    start: dt.date,
    end: dt.date,
) -> pd.DataFrame:

    df = RegimeRepository().fetch_symbol(_raw_symbol(symbol))

    if df.empty:
        raise NotImplementedError(
            f"No regime data available for {symbol!r} yet -- "
            f"run the regime pipeline for this symbol."
        )

    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df = _filter_date_range(df, "trade_date", start, end)
    df = df.sort_values("trade_date")
    df = df.rename(columns={"risk_regime": "regime"})

    return df.set_index("trade_date")


# ==========================================================
# MODEL VALIDATION
# ==========================================================

@st.cache_data(ttl=300, show_spinner=False)
def get_validation_summary(
    symbol: str,
    method: str,
    end_date: dt.date,
) -> dict:
    """
    Runs Kupiec / Christoffersen / Conditional Coverage over the full
    hit sequence up to end_date (not just the sidebar's date range --
    a model validation backtest wants as much history as exists, not
    a truncated window the analyst happens to be charting).
    """
    hit_df = _load_var_breach_series(symbol, method, "95")
    hit_df = hit_df[hit_df.index <= pd.Timestamp(end_date)]

    if hit_df.empty:
        raise NotImplementedError(
            f"No breach history for {symbol!r} on or before {end_date} "
            f"to validate against."
        )

    breaches = hit_df["breach"].astype(int).tolist()

    kupiec = ModelValidation.kupiec_test(breaches, confidence_level=VAR_CONFIDENCE)
    christoffersen = ModelValidation.christoffersen_test(breaches)
    conditional = ModelValidation.conditional_coverage_test(breaches, confidence_level=VAR_CONFIDENCE)

    def _shape(result: dict) -> dict:
        # Christoffersen/conditional coverage can be degenerate (e.g.
        # zero breaches in the sample) -- lr_statistic/p_value come back
        # as None in that case. NaN keeps the ":.4f" formatting in
        # render_validation_table from crashing on a None.
        if result["passed"] is None:
            return {"result": "N/A", "statistic": float("nan"), "p_value": float("nan")}
        return {
            "result": "PASS" if result["passed"] else "FAIL",
            "statistic": result["lr_statistic"],
            "p_value": result["p_value"],
        }

    return {
        "kupiec": _shape(kupiec),
        "christoffersen": _shape(christoffersen),
        "conditional_coverage": _shape(conditional),
    }


# ==========================================================
# BASEL TRAFFIC LIGHT
# ==========================================================

@st.cache_data(ttl=300, show_spinner=False)
def get_basel_traffic_light(
    symbol: str,
    method: str,
    start_date: dt.date,
    end_date: dt.date,
) -> pd.DataFrame:
    """
    Rolling 250-day Basel traffic-light zone/multiplier/exception-count
    series. Basel's boundaries are only rigorously defined at the 99%
    confidence level (see ModelValidation.basel_traffic_light), so this
    always uses the 99% VaR column regardless of the method's own
    confidence-level toggle elsewhere in the UI.
    """
    hit_df = _load_var_breach_series(symbol, method, _BASEL_CONFIDENCE_SUFFIX)

    exceptions = hit_df["breach"].astype(int).rolling(_BASEL_WINDOW).sum()
    valid = exceptions.dropna()

    if valid.empty:
        raise NotImplementedError(
            f"Fewer than {_BASEL_WINDOW} observations for {symbol!r} -- "
            f"not enough history yet for a full Basel window."
        )

    def _zone_row(n: float):
        result = ModelValidation.basel_traffic_light(int(n), _BASEL_WINDOW)
        return result["zone"].upper(), result["capital_multiplier"]

    zones, multipliers = zip(*(_zone_row(n) for n in valid))

    result = pd.DataFrame(
        {
            "breach_count": valid.astype(int),
            "zone": zones,
            "risk_multiplier": multipliers,
        },
        index=valid.index,
    )
    result.index.name = "trade_date"

    result = result[
        (result.index >= pd.Timestamp(start_date)) & (result.index <= pd.Timestamp(end_date))
    ]

    if result.empty:
        raise NotImplementedError(
            f"No Basel window data for {symbol!r} in range "
            f"{start_date}-{end_date} -- widen the date range."
        )

    return result


# ==========================================================
# RECENT RISK EVENTS
# ==========================================================

@st.cache_data(ttl=300, show_spinner=False)
def get_recent_risk_events(
    symbol: str,
) -> pd.DataFrame:
    """
    SENTINEL has no dedicated event-log table -- this derives an event
    feed from two things that already exist: VaR breaches (a concrete,
    dated occurrence) and elevated risk_level readings (HIGH/EXTREME)
    from the risk score pipeline. If a real event log table is added
    later, replace this with a straight fetch_symbol() call.
    """
    risk = RiskScoreRepository().fetch_symbol(_raw_symbol(symbol))
    if risk.empty:
        raise NotImplementedError(
            f"No risk score data available for {symbol!r} yet -- "
            f"run the risk score pipeline for this symbol."
        )
    risk["trade_date"] = pd.to_datetime(risk["trade_date"])

    events = []

    for _, row in risk[risk["risk_level"].isin(["HIGH", "EXTREME"])].iterrows():
        severity = "Critical" if row["risk_level"] == "EXTREME" else "Warning"
        events.append(
            {
                "date": row["trade_date"],
                "event_type": "Risk Level Escalation",
                "description": (
                    f"Composite risk score {row['total_score']:.1f} "
                    f"({row['risk_level']})"
                ),
                "severity": severity,
            }
        )

    try:
        hit_df = _load_var_breach_series(symbol, "historical", "95")
        breaches = hit_df[hit_df["breach"]]
        for trade_date, row in breaches.iterrows():
            magnitude = row["simple_return"]
            severity = "Critical" if magnitude < 2 * row["var_value"] else "Warning"
            events.append(
                {
                    "date": trade_date,
                    "event_type": "VaR Breach",
                    "description": f"Return {magnitude:+.2%} breached 95% Historical VaR",
                    "severity": severity,
                }
            )
    except NotImplementedError:
        # VaR history may not be wired for every symbol -- risk-level
        # events above still stand on their own.
        pass

    if not events:
        return pd.DataFrame(columns=["date", "event_type", "description", "severity"])

    events_df = pd.DataFrame(events)
    return (
        events_df.sort_values("date", ascending=False)
        .head(25)
        .reset_index(drop=True)
    )


# ==========================================================
# DATABASE EXPLORER (raw table browser)
# ==========================================================

@st.cache_data(ttl=300, show_spinner=False)
def get_market_data_table(
    symbols: list,
    start_date: dt.date,
    end_date: dt.date,
) -> pd.DataFrame:
    """
    Raw market price rows for one or more symbols, flat (not indexed)
    so components.tables.render_explorer_table can search/sort/filter/
    paginate/export it directly.
    """
    repo = MarketRepository()
    frames = [repo.fetch_symbol(_raw_symbol(s)) for s in symbols]
    frames = [f for f in frames if not f.empty]

    if not frames:
        raise NotImplementedError(
            f"No market price data available for {symbols!r} yet -- "
            f"run the market data pipeline for these symbols."
        )

    df = pd.concat(frames, ignore_index=True)
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df = _filter_date_range(df, "trade_date", start_date, end_date)
    # Show the same clean symbol the analyst picked in the multiselect,
    # not the raw Yahoo Finance ticker stored in the DB.
    df["symbol"] = df["symbol"].map(_display_symbol)
    df = df.sort_values(["symbol", "trade_date"]).reset_index(drop=True)

    return df