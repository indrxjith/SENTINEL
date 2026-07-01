"""
services/derived.py
====================
IMPORTANT — read this before adding anything here.

This module does NOT compute risk metrics. It never touches VaR,
Expected Shortfall, Correlation, Beta, Regime Detection, Composite Risk
Score, or Model Validation — those come exclusively from data_loader.py,
which reads them from src/analytics and src/validation.

What lives here is generic, model-free post-processing applied to data
the backend has already returned: sorting, grouping, counting
transitions, bucketing a histogram, computing a running maximum. The
distinction that matters: everything in this file takes a DataFrame/
Series as input and would give the identical answer no matter which
quant platform produced that input — there is no market-risk modeling
judgment involved.

Two functions here (drawdown, tail losses) are borderline: if your
src/analytics module already computes these, redirect the equivalent
data_loader.py function to it instead and drop the local computation
below — flagged inline where relevant.
"""

from __future__ import annotations

import pandas as pd


# ---------------------------------------------------------------------------
# Returns / drawdown / tail losses
# ---------------------------------------------------------------------------
def compute_returns(price_df: pd.DataFrame) -> pd.Series:
    """Daily simple returns from a close price column. Pure arithmetic
    transform, not a risk metric."""
    return price_df["close"].pct_change().dropna().rename("return")


def compute_drawdown(price_df: pd.DataFrame) -> pd.Series:
    """
    Running drawdown from the rolling peak: (price / running_max) - 1.

    NOTE: if src/analytics already exposes a drawdown series, prefer
    wiring data_loader.get_drawdown() to that instead of this local
    computation, for consistency with whatever convention (log vs
    simple returns, peak-to-trough windowing) your backend uses.
    """
    close = price_df["close"]
    running_max = close.cummax()
    return ((close / running_max) - 1).rename("drawdown")


def compute_tail_losses(returns: pd.Series, n: int = 10) -> pd.DataFrame:
    """
    Returns the n worst single-period returns, sorted worst first.
    Pure sort/slice — no modeling.
    """
    worst = returns.nsmallest(n)
    return pd.DataFrame({"date": worst.index, "return": worst.values}).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Transitions (regime timeline, Basel traffic light)
# ---------------------------------------------------------------------------
def compute_transition_matrix(categorical_series: pd.Series) -> pd.DataFrame:
    """
    Given a time-ordered series of category labels (e.g. Basel zones or
    market regimes), returns a square DataFrame of transition COUNTS:
    matrix.loc[from_state, to_state] = number of times the series moved
    from from_state to to_state on consecutive observations.

    This is plain counting over already-labeled data, not a Markov model
    fit or any statistical estimation.
    """
    states = sorted(categorical_series.dropna().unique())
    matrix = pd.DataFrame(0, index=states, columns=states)

    values = categorical_series.dropna().tolist()
    for prev, curr in zip(values[:-1], values[1:]):
        matrix.loc[prev, curr] += 1

    matrix.index.name = "From"
    matrix.columns.name = "To"
    return matrix


def compute_regime_segments(regime_df: pd.DataFrame) -> pd.DataFrame:
    """
    Collapses a per-date regime column into contiguous segments, for
    drawing a timeline instead of one mark per day.

    Return contract:
        DataFrame with columns: regime, start_date, end_date
    """
    df = regime_df.copy()
    df["_block"] = (df["regime"] != df["regime"].shift()).cumsum()

    segments = (
        df.reset_index()
        .groupby("_block")
        .agg(regime=("regime", "first"), start_date=(df.index.name or "index", "first"), end_date=(df.index.name or "index", "last"))
        .reset_index(drop=True)
    )
    return segments


# ---------------------------------------------------------------------------
# Basel-specific derived summaries (built on data_loader.get_basel_traffic_light output)
# ---------------------------------------------------------------------------
def compute_conditional_breach_probability(basel_df: pd.DataFrame, window: int) -> float:
    """
    Simple ratio: total breaches observed / total observation-days in
    the window. A descriptive statistic over the already-computed breach
    counts, not a re-derivation of Kupiec/Christoffersen.
    """
    total_breaches = basel_df["breach_count"].sum()
    total_days = len(basel_df) * window
    return float(total_breaches) / total_days if total_days else 0.0


def find_worst_basel_window(basel_df: pd.DataFrame) -> dict:
    """
    Returns the row with the highest risk_multiplier (i.e. the worst
    Basel window on record in the loaded range) as a plain dict.
    """
    if basel_df.empty:
        return {}
    worst_row = basel_df.loc[basel_df["risk_multiplier"].idxmax()]
    return {
        "date": worst_row.name,
        "zone": worst_row["zone"],
        "breach_count": int(worst_row["breach_count"]),
        "risk_multiplier": float(worst_row["risk_multiplier"]),
    }
