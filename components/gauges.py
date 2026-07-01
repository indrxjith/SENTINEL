"""
components/gauges.py
=====================
Gauge/indicator visuals — currently the composite Risk Score dial used
on the Overview page. Takes a score value (already computed by
src/analytics) and a scale; renders only.
"""

from __future__ import annotations

import plotly.graph_objects as go

from config import COLORS, FONTS


def build_risk_score_gauge(score: float, scale_max: float = 100.0, label: str = "Composite Risk Score") -> go.Figure:
    """
    `score` must already be on a 0..scale_max scale as produced by the
    backend's composite risk score function — this component does not
    normalize, clamp, or reinterpret the value.
    """
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            number=dict(font=dict(family=FONTS.mono, color=COLORS.text_primary, size=28)),
            gauge=dict(
                axis=dict(range=[0, scale_max], tickfont=dict(family=FONTS.mono, color=COLORS.text_secondary, size=10)),
                bar=dict(color=COLORS.blue, thickness=0.25),
                bgcolor="rgba(0,0,0,0)",
                borderwidth=1,
                bordercolor=COLORS.border,
                steps=[
                    dict(range=[0, scale_max * 0.4], color="rgba(0,200,83,0.12)"),
                    dict(range=[scale_max * 0.4, scale_max * 0.7], color="rgba(255,179,0,0.12)"),
                    dict(range=[scale_max * 0.7, scale_max], color="rgba(255,77,77,0.12)"),
                ],
            ),
            title=dict(text=label, font=dict(family=FONTS.body, color=COLORS.text_secondary, size=12)),
        )
    )
    fig.update_layout(height=200, margin=dict(l=20, r=20, t=40, b=10))
    return fig
