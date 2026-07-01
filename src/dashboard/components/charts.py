"""
components/charts.py
=====================
Plotly figure builders. Every function here takes already-computed
DataFrames/Series (from data_loader, via a page) and returns a
go.Figure — no data fetching, no risk math, purely presentation.

All figures use the shared "sentinel_dark" template registered in
theme.py, so they don't redeclare colors/fonts individually.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from config import COLORS


def build_price_risk_chart(
    price_df: pd.DataFrame,
    var_df: pd.DataFrame | None = None,
    es_df: pd.DataFrame | None = None,
) -> go.Figure:
    """
    Main Overview chart: close price with VaR / Expected Shortfall bands
    overlaid on a secondary axis, plus breach markers where var_df['breach']
    is True.

    Parameters
    ----------
    price_df : output of data_loader.get_price_history() — needs a 'close' column
    var_df   : output of data_loader.get_var() — needs 'var', 'breach' columns (optional)
    es_df    : output of data_loader.get_expected_shortfall() — needs 'expected_shortfall' (optional)
    """
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=price_df.index,
            y=price_df["close"],
            name="Price",
            mode="lines",
            line=dict(color=COLORS.blue, width=1.5),
            yaxis="y1",
            hovertemplate="%{y:.2f}<extra>Price</extra>",
        )
    )

    if var_df is not None and "var" in var_df.columns:
        fig.add_trace(
            go.Scatter(
                x=var_df.index,
                y=var_df["var"],
                name="Historical VaR",
                mode="lines",
                line=dict(color=COLORS.amber, width=1, dash="dot"),
                yaxis="y2",
                hovertemplate="%{y:.2f}<extra>VaR</extra>",
            )
        )

        if "breach" in var_df.columns:
            breaches = var_df[var_df["breach"]]
            if not breaches.empty:
                breach_prices = price_df.loc[price_df.index.intersection(breaches.index), "close"]
                fig.add_trace(
                    go.Scatter(
                        x=breach_prices.index,
                        y=breach_prices.values,
                        name="VaR Breach",
                        mode="markers",
                        marker=dict(color=COLORS.red, size=7, symbol="x"),
                        yaxis="y1",
                        hovertemplate="Breach<extra></extra>",
                    )
                )

    if es_df is not None and "expected_shortfall" in es_df.columns:
        fig.add_trace(
            go.Scatter(
                x=es_df.index,
                y=es_df["expected_shortfall"],
                name="Expected Shortfall",
                mode="lines",
                line=dict(color=COLORS.purple, width=1, dash="dash"),
                yaxis="y2",
                hovertemplate="%{y:.2f}<extra>ES</extra>",
            )
        )

    fig.update_layout(
        height=440,
        yaxis=dict(title="Price", side="left"),
        yaxis2=dict(title="Risk", overlaying="y", side="right", showgrid=False),
        xaxis=dict(rangeslider=dict(visible=False)),
        hovermode="x unified",
    )
    return fig


def build_sparkline(series: pd.Series, color: str = COLORS.blue) -> go.Figure:
    """Minimal no-axis sparkline for compact card contexts."""
    fig = go.Figure(
        go.Scatter(x=series.index, y=series.values, mode="lines", line=dict(color=color, width=1.5))
    )
    fig.update_layout(
        height=60,
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        showlegend=False,
    )
    return fig
