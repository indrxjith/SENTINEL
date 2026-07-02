"""
data_loader.py

Single bridge between the Streamlit dashboard and PostgreSQL.
Every dashboard page should ONLY import from this file.
"""

from __future__ import annotations

import datetime as dt
from typing import Literal

import pandas as pd
import streamlit as st
from sqlalchemy import text

from src.utils.database import engine

from src.repository.market_repository import MarketRepository
from src.repository.var_repository import VarRepository
from src.repository.expected_shortfall_repository import (
    ExpectedShortfallRepository,
)
from src.repository.beta_repository import BetaRepository
from src.repository.correlation_repository import CorrelationRepository
from src.repository.feature_repository import FeatureRepository
from src.repository.regime_repository import RegimeRepository
from src.repository.risk_score_repository import RiskScoreRepository


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
# PRICE HISTORY
# ==========================================================

@st.cache_data(ttl=300, show_spinner=False)
def get_price_history(
    symbol: str,
    start: dt.date,
    end: dt.date,
) -> pd.DataFrame:

    repo = MarketRepository()

    df = repo.fetch_symbol(symbol)

    if df.empty:
        return df

    df["trade_date"] = pd.to_datetime(df["trade_date"])

    df = df[
        (df.trade_date >= pd.Timestamp(start))
        &
        (df.trade_date <= pd.Timestamp(end))
    ]

    df = df.set_index("trade_date")

    return df


# ==========================================================
# VALUE AT RISK
# ==========================================================

@st.cache_data(ttl=300, show_spinner=False)
def get_var(
    symbol: str,
    method: Literal["historical", "parametric"],
    start: dt.date,
    end: dt.date,
    confidence: float = 0.95,
) -> pd.DataFrame:

    price_repo = MarketRepository()
    var_repo = VarRepository()

    prices = price_repo.fetch_symbol(symbol)
    var = var_repo.fetch_symbol(symbol)

    if prices.empty or var.empty:
        return pd.DataFrame()

    prices["trade_date"] = pd.to_datetime(prices["trade_date"])
    var["trade_date"] = pd.to_datetime(var["trade_date"])

    if method == "historical":
        column = (
            "historical_var_95"
            if confidence <= 0.95
            else "historical_var_99"
        )
    else:
        column = (
            "parametric_var_95"
            if confidence <= 0.95
            else "parametric_var_99"
        )

    df = prices.merge(
        var[
            [
                "trade_date",
                column,
            ]
        ],
        on="trade_date",
    )

    df = df[
        (df.trade_date >= pd.Timestamp(start))
        &
        (df.trade_date <= pd.Timestamp(end))
    ]

    df["var"] = df[column].abs()

    returns = df["close"].pct_change()

    df["breach"] = (
        returns <
        (-df["var"] / 100)
    )

    df = df.set_index("trade_date")

    return df[
        [
            "var",
            "close",
            "breach",
        ]
    ].rename(
        columns={
            "close": "price",
        }
    )


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

    price_repo = MarketRepository()
    es_repo = ExpectedShortfallRepository()

    prices = price_repo.fetch_symbol(symbol)
    es = es_repo.fetch_symbol(symbol)

    if prices.empty or es.empty:
        return pd.DataFrame()

    prices["trade_date"] = pd.to_datetime(prices["trade_date"])
    es["trade_date"] = pd.to_datetime(es["trade_date"])

    column = (
        "expected_shortfall_95"
        if confidence <= 0.95
        else "expected_shortfall_99"
    )

    df = prices.merge(
        es[
            [
                "trade_date",
                column,
            ]
        ],
        on="trade_date",
    )

    df = df[
        (df.trade_date >= pd.Timestamp(start))
        &
        (df.trade_date <= pd.Timestamp(end))
    ]

    df = df.set_index("trade_date")

    return df[
        [
            column,
            "close",
        ]
    ].rename(
        columns={
            column: "expected_shortfall",
            "close": "price",
        }
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

    repo = FeatureRepository()

    df = repo.fetch_symbol(symbol)

    if df.empty:
        return pd.Series(dtype=float)

    df["trade_date"] = pd.to_datetime(df["trade_date"])

    df = df[
        (df.trade_date >= pd.Timestamp(start))
        &
        (df.trade_date <= pd.Timestamp(end))
    ]

    if window <= 20:
        column = "annualized_volatility_20d"
    elif window <= 60:
        column = "annualized_volatility_60d"
    else:
        column = "annualized_volatility_252d"

    return pd.Series(
        df[column].values,
        index=df["trade_date"],
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

    repo = BetaRepository()

    df = repo.fetch_symbol(symbol)

    if df.empty:
        return 0.0

    df = df[df["benchmark"] == benchmark]

    if df.empty:
        return 0.0

    return float(df.iloc[-1]["beta_252"])


# ==========================================================
# RISK SCORE
# ==========================================================

@st.cache_data(ttl=300, show_spinner=False)
def get_risk_score(
    symbol: str,
    as_of: dt.date,
) -> dict:

    repo = RiskScoreRepository()

    df = repo.fetch_symbol(symbol)

    if df.empty:
        return {}

    df["trade_date"] = pd.to_datetime(df["trade_date"])

    df = df[
        df.trade_date <= pd.Timestamp(as_of)
    ]

    if df.empty:
        return {}

    latest = df.iloc[-1]

    return {
        "score": float(latest["total_score"]),
        "label": latest["risk_level"],
        "components": {
            "volatility": float(latest["volatility_score"]),
            "drawdown": float(latest["drawdown_score"]),
            "beta": float(latest["beta_score"]),
            "var": float(latest["var_score"]),
            "expected_shortfall": float(
                latest["expected_shortfall_score"]
            ),
        },
    }

# ==========================================================
# CORRELATION MATRIX
# ==========================================================

@st.cache_data(ttl=300, show_spinner=False)
def get_correlation_matrix(
    symbols: list[str],
    start: dt.date,
    end: dt.date,
) -> pd.DataFrame:

    repo = CorrelationRepository()

    df = repo.fetch_all()

    if df.empty:
        return pd.DataFrame()

    df["trade_date"] = pd.to_datetime(df["trade_date"])

    df = df[
        (df.trade_date >= pd.Timestamp(start))
        &
        (df.trade_date <= pd.Timestamp(end))
    ]

    latest_date = df["trade_date"].max()

    df = df[df["trade_date"] == latest_date]

    matrix = pd.DataFrame(
        index=symbols,
        columns=symbols,
        dtype=float,
    )

    for s in symbols:
        matrix.loc[s, s] = 1.0

    for _, row in df.iterrows():

        a = row["asset_1"]
        b = row["asset_2"]

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

    repo = CorrelationRepository()

    df = repo.fetch_all()

    if df.empty:
        return pd.Series(dtype=float)

    df["trade_date"] = pd.to_datetime(df["trade_date"])

    df = df[
        (
            ((df.asset_1 == symbol_a) & (df.asset_2 == symbol_b))
            |
            ((df.asset_1 == symbol_b) & (df.asset_2 == symbol_a))
        )
    ]

    df = df[
        (df.trade_date >= pd.Timestamp(start))
        &
        (df.trade_date <= pd.Timestamp(end))
    ]

    if window <= 20:
        column = "rolling_corr_20"
    elif window <= 60:
        column = "rolling_corr_60"
    else:
        column = "rolling_corr_252"

    return pd.Series(
        df[column].values,
        index=df["trade_date"],
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

    repo = RegimeRepository()

    df = repo.fetch_symbol(symbol)

    if df.empty:
        return pd.DataFrame()

    df["trade_date"] = pd.to_datetime(df["trade_date"])

    df = df[
        (df.trade_date >= pd.Timestamp(start))
        &
        (df.trade_date <= pd.Timestamp(end))
    ]
    df = df.rename(
    columns={
        "risk_regime": "regime"
    }
)

    df = df.set_index("trade_date")

    return df


# ==========================================================
# MODEL VALIDATION
# ==========================================================

@st.cache_data(ttl=300, show_spinner=False)
def get_validation_summary(
    symbol: str,
    method: str,
    end_date: dt.date,
):

    var_df = get_var(
        symbol=symbol,
        method=method.lower(),
        start=dt.date(2000, 1, 1),
        end=end_date,
    )

    if var_df.empty:

        return {
            "observations": 0,
            "breaches": 0,
            "breach_rate": 0.0,
            "expected_rate": 0.05,
        }

    breaches = int(var_df["breach"].sum())

    observations = len(var_df)

    return {
        "observations": observations,
        "breaches": breaches,
        "breach_rate": breaches / observations if observations else 0,
        "expected_rate": 0.05,
    }


# ==========================================================
# BASEL TRAFFIC LIGHT
# ==========================================================

@st.cache_data(ttl=300, show_spinner=False)
def get_basel_traffic_light(
    symbol: str,
    method: str,
    end_date: dt.date,
):

    summary = get_validation_summary(
        symbol,
        method,
        end_date,
    )

    breaches = summary["breaches"]

    if breaches <= 4:
        zone = "Green"
    elif breaches <= 9:
        zone = "Yellow"
    else:
        zone = "Red"

    return {
        "zone": zone,
        "breaches": breaches,
    }


# ==========================================================
# RECENT RISK EVENTS
# ==========================================================

@st.cache_data(ttl=300, show_spinner=False)
def get_recent_risk_events(
    symbol: str,
):

    risk = RiskScoreRepository().fetch_symbol(symbol)

    if risk.empty:
        return pd.DataFrame()

    risk["trade_date"] = pd.to_datetime(risk["trade_date"])

    return (
        risk.sort_values("trade_date", ascending=False)
            .head(25)
            .reset_index(drop=True)
    )