"""
Trend feature engineering module.

Calculates trend and momentum indicators.
"""

from __future__ import annotations

import pandas as pd

from src.features.base import BaseFeatureEngineer


class TrendCalculator(BaseFeatureEngineer):
    """
    Calculates trend-based features.
    """

    def calculate(
        self,
        data: pd.DataFrame,
    ) -> pd.DataFrame:

        data = self.prepare_data(data)

        price = data["adjusted_close"]

        # ============================
        # Simple Moving Averages
        # ============================

        data["sma_20"] = price.rolling(20).mean()
        data["sma_50"] = price.rolling(50).mean()
        data["sma_200"] = price.rolling(200).mean()

        # ============================
        # Exponential Moving Averages
        # ============================

        data["ema_20"] = price.ewm(span=20, adjust=False).mean()
        data["ema_50"] = price.ewm(span=50, adjust=False).mean()

        # ============================
        # Momentum
        # ============================

        data["momentum_20"] = price - price.shift(20)

        # ============================
        # Rate of Change
        # ============================

        data["roc_20"] = price.pct_change(20)

        # ============================
        # Distance from Moving Averages
        # ============================

        data["distance_sma20"] = (
            (price - data["sma_20"])
            / data["sma_20"]
        )

        data["distance_sma50"] = (
            (price - data["sma_50"])
            / data["sma_50"]
        )

        data["distance_sma200"] = (
            (price - data["sma_200"])
            / data["sma_200"]
        )

        return data


# ==========================================================
# Test
# ==========================================================

if __name__ == "__main__":

    from src.repository.market_repository import MarketRepository

    repository = MarketRepository()

    df = repository.fetch_symbol("SPY")

    calculator = TrendCalculator()

    df = calculator.calculate(df)

    print(df.tail())

    print("\nTrend Columns:\n")

    trend_columns = [
        column
        for column in df.columns
        if (
            "sma" in column
            or "ema" in column
            or "momentum" in column
            or "roc" in column
        )
    ]

    print(trend_columns)