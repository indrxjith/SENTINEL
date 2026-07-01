"""
config.py
=========
Single source of truth for SENTINEL's static configuration: the color
system, typography, asset universe, and default parameters. Nothing in
this module talks to the database or performs calculations — it only
describes the platform's constants so every other module (theme, pages,
components) references the same values instead of re-declaring them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final


# ---------------------------------------------------------------------------
# Color system
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Colors:
    """Institutional dark-mode palette. Do not add colors outside this set —
    the whole point of a terminal-grade UI is a disciplined, narrow palette."""

    background: str = "#090909"
    surface: str = "#111111"          # card background
    border: str = "#202020"           # card border / hairline rules
    text_primary: str = "#F5F5F5"
    text_secondary: str = "#A0A0A0"

    blue: str = "#2E86FF"     # primary accent / price series
    green: str = "#00C853"    # positive / PASS / bull
    red: str = "#FF4D4D"      # negative / FAIL / breach
    amber: str = "#FFB300"    # caution / YELLOW traffic light
    purple: str = "#7C4DFF"   # secondary series / regime markers

    @property
    def risk_scale(self) -> list[str]:
        """Low -> high risk color ramp, used by gauges and heatmaps."""
        return [self.green, self.amber, self.red]


COLORS: Final = Colors()


# ---------------------------------------------------------------------------
# Typography
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Fonts:
    body: str = "'IBM Plex Sans', -apple-system, sans-serif"
    heading: str = "'IBM Plex Sans', -apple-system, sans-serif"
    mono: str = "'JetBrains Mono', 'IBM Plex Mono', 'Courier New', monospace"


FONTS: Final = Fonts()

GOOGLE_FONTS_URL: Final = (
    "https://fonts.googleapis.com/css2?"
    "family=IBM+Plex+Sans:wght@400;500;600;700&"
    "family=IBM+Plex+Mono:wght@400;500;600&"
    "family=JetBrains+Mono:wght@400;500;600&display=swap"
)


# ---------------------------------------------------------------------------
# Asset universe / defaults
# ---------------------------------------------------------------------------
ASSET_UNIVERSE: Final[list[str]] = ["SPY", "QQQ", "BTC", "GLD", "USO", "VIX", "TNX", "DXY"]

MODEL_OPTIONS: Final[list[str]] = ["Historical", "Parametric", "Expected Shortfall"]

DEFAULT_ASSET: Final[str] = "SPY"
DEFAULT_MODEL: Final[str] = "Historical"
DEFAULT_LOOKBACK_DAYS: Final[int] = 252  # ~1 trading year

VAR_CONFIDENCE: Final[float] = 0.95
ES_CONFIDENCE: Final[float] = 0.975

APP_TITLE: Final[str] = "SENTINEL"
APP_SUBTITLE: Final[str] = "Market Risk Intelligence Platform"

NAV_PAGES: Final[list[str]] = [
    "Overview",
    "Risk Analytics",
    "Model Validation",
    "Correlation",
    "Market Regimes",
    "Database Explorer",
    "About",
]


@dataclass(frozen=True)
class DBSettings:
    """Placeholder connection descriptor. Wire this to your existing
    SQLAlchemy engine / session factory in data_loader.py — SENTINEL's
    frontend never opens its own connection logic beyond this pointer."""

    dsn_env_var: str = "SENTINEL_DATABASE_URL"
    schema: str = "public"


DB_SETTINGS: Final = DBSettings()
