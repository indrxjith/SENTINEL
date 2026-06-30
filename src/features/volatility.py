"""
Volatility feature engineering module.

Calculates rolling volatility features.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.features.base import BaseFeatureEngineer


class VolatilityCalculator(BaseFeatureEngineer):
    """
    Calculates volatility-based features.
    """

    WINDOWS = [20, 60, 252]

    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate volatility features.
        """

        data = self.prepare_data(data)

        # Calculate returns if not already present
        if "simple_return" not in data.columns:
            data["simple_return"] = (
                data["adjusted_close"].pct_change()
            )

        # Rolling volatility
        for window in self.WINDOWS:

            data[f"volatility_{window}d"] = (
                data["simple_return"]
                .rolling(window)
                .std()
            )

        # Annualized volatility
        for window in self.WINDOWS:

            data[f"annualized_volatility_{window}d"] = (
                data[f"volatility_{window}d"]
                * np.sqrt(252)
            )

        # Volatility acceleration
        data["volatility_acceleration"] = (
            data["volatility_20d"]
            - data["volatility_60d"]
        )

        return data


# ==========================================================
# Test
# ==========================================================

if __name__ == "__main__":

    from src.features.returns import ReturnCalculator
    from src.repository.market_repository import MarketRepository

    repository = MarketRepository()

    df = repository.fetch_symbol("SPY")

    returns = ReturnCalculator()
    df = returns.calculate_all(df)

    volatility = VolatilityCalculator()

    df = volatility.calculate(df)

    print(df.head(30))

    print("\nNew Volatility Columns:\n")

    print(
        [
            column
            for column in df.columns
            if "volatility" in column
        ]
    )