"""
Drawdown feature engineering module.
"""

from __future__ import annotations

import pandas as pd

from src.features.base import BaseFeatureEngineer


class DrawdownCalculator(BaseFeatureEngineer):
    """
    Calculates drawdown-related features.
    """

    def calculate(
        self,
        data: pd.DataFrame,
    ) -> pd.DataFrame:

        data = self.prepare_data(data)

        # Running peak
        data["rolling_peak"] = (
            data["adjusted_close"].cummax()
        )

        # Current drawdown
        data["drawdown"] = (
            data["adjusted_close"]
            / data["rolling_peak"]
            - 1
        )

        # Running maximum drawdown
        data["max_drawdown"] = (
            data["drawdown"].cummin()
        )

        return data


# ==========================================================
# Test
# ==========================================================

if __name__ == "__main__":

    from src.repository.market_repository import MarketRepository

    repository = MarketRepository()

    df = repository.fetch_symbol("SPY")

    calculator = DrawdownCalculator()

    df = calculator.calculate(df)

    print(df.head(30))

    print("\nDrawdown Columns:\n")

    print(
        [
            c
            for c in df.columns
            if "drawdown" in c
            or "peak" in c
        ]
    )