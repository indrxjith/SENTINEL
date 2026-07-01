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

from config import COLORS, FONTS


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


def build_rolling_line_chart(
    series: pd.Series, name: str, color: str = COLORS.blue, y_title: str | None = None
) -> go.Figure:
    """Generic single-line time series chart — used for rolling VaR,
    rolling ES, rolling volatility, and rolling correlation, all of
    which share the same visual shape."""
    fig = go.Figure(
        go.Scatter(
            x=series.index,
            y=series.values,
            name=name,
            mode="lines",
            line=dict(color=color, width=1.5),
            hovertemplate="%{y:.4f}<extra>" + name + "</extra>",
        )
    )
    fig.update_layout(height=320, yaxis=dict(title=y_title or name), hovermode="x unified")
    return fig


def build_distribution_histogram(returns: pd.Series, bins: int = 60) -> go.Figure:
    """Return distribution histogram with a marked mean line — used on
    the Risk Analytics page."""
    fig = go.Figure(
        go.Histogram(
            x=returns.values,
            nbinsx=bins,
            marker=dict(color=COLORS.blue, line=dict(color=COLORS.border, width=0.5)),
            hovertemplate="Return: %{x:.4f}<br>Count: %{y}<extra></extra>",
        )
    )
    mean_return = returns.mean()
    fig.add_vline(
        x=mean_return,
        line=dict(color=COLORS.amber, width=1.5, dash="dash"),
        annotation_text=f"mean {mean_return:.4f}",
        annotation_font=dict(family=FONTS.mono, color=COLORS.amber, size=11),
    )
    fig.update_layout(height=320, xaxis=dict(title="Daily Return"), yaxis=dict(title="Frequency"), showlegend=False)
    return fig


def build_drawdown_chart(drawdown: pd.Series) -> go.Figure:
    """Filled area drawdown chart, always negative-going, red-shaded."""
    fig = go.Figure(
        go.Scatter(
            x=drawdown.index,
            y=drawdown.values,
            mode="lines",
            line=dict(color=COLORS.red, width=1),
            fill="tozeroy",
            fillcolor="rgba(255,77,77,0.15)",
            hovertemplate="%{y:.2%}<extra>Drawdown</extra>",
        )
    )
    fig.update_layout(height=280, yaxis=dict(title="Drawdown", tickformat=".0%"), showlegend=False)
    return fig


def build_correlation_heatmap(corr_matrix: pd.DataFrame) -> go.Figure:
    """Diverging heatmap for the correlation matrix — blue/red so
    positive and negative correlation read at a glance."""
    fig = go.Figure(
        go.Heatmap(
            z=corr_matrix.values,
            x=corr_matrix.columns.tolist(),
            y=corr_matrix.index.tolist(),
            zmin=-1,
            zmax=1,
            colorscale=[[0, COLORS.red], [0.5, COLORS.surface], [1, COLORS.blue]],
            colorbar=dict(
                thickness=12,
                outlinewidth=0,
                tickfont=dict(family=FONTS.mono, color=COLORS.text_secondary, size=10),
            ),
            hovertemplate="%{y} × %{x}: %{z:.2f}<extra></extra>",
        )
    )
    fig.update_layout(
        height=max(360, 40 * len(corr_matrix)),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=False, autorange="reversed"),
    )
    return fig


def build_regime_timeline(segments: pd.DataFrame) -> go.Figure:
    """
    Horizontal segment timeline for market regimes.

    `segments` must have columns: regime, start_date, end_date (the
    output of services.derived.compute_regime_segments).
    """
    regime_colors = {
        "Bull": COLORS.green,
        "Bear": COLORS.red,
        "High Volatility": COLORS.amber,
        "Low Volatility": COLORS.blue,
    }

    fig = go.Figure()
    for _, row in segments.iterrows():
        color = regime_colors.get(row["regime"], COLORS.purple)
        fig.add_trace(
            go.Scatter(
                x=[row["start_date"], row["end_date"]],
                y=[row["regime"], row["regime"]],
                mode="lines",
                line=dict(color=color, width=14),
                showlegend=False,
                hovertemplate=f"{row['regime']}<br>%{{x}}<extra></extra>",
            )
        )

    fig.update_layout(
        height=220,
        yaxis=dict(title=None, showgrid=False),
        xaxis=dict(title=None),
    )
    return fig
