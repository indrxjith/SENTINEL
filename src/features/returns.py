"""
Return calculation module for the SENTINEL project.

Calculates return-based financial features.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.features.base import BaseFeatureEngineer


class ReturnCalculator(BaseFeatureEngineer):
    """
    Calculates return-based features.
    """

    def simple_return(
        self,
        data: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Calculate daily simple returns.
        """

        data = self.prepare_data(data)

        data["simple_return"] = (
            data["adjusted_close"]
            .pct_change()
        )

        return data

    # -----------------------------------------------------

    def log_return(
        self,
        data: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Calculate daily log returns.
        """

        data = self.prepare_data(data)

        data["log_return"] = np.log(
            data["adjusted_close"]
            / data["adjusted_close"].shift(1)
        )

        return data

    # -----------------------------------------------------

    def cumulative_return(
        self,
        data: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Calculate cumulative return.
        """

        data = self.prepare_data(data)

        first_price = data["adjusted_close"].iloc[0]

        data["cumulative_return"] = (
            data["adjusted_close"] / first_price
        ) - 1

        return data

    # -----------------------------------------------------

    def rolling_returns(
        self,
        data: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Calculate rolling returns.
        """

        data = self.prepare_data(data)

        windows = [5, 20, 60, 252]

        for window in windows:

            data[f"return_{window}d"] = (
                data["adjusted_close"]
                .pct_change(window)
            )

        return data

    # -----------------------------------------------------

    def calculate_all(
        self,
        data: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Calculate every return feature.
        """

        data = self.simple_return(data)
        data = self.log_return(data)
        data = self.cumulative_return(data)
        data = self.rolling_returns(data)

        return data


# ==========================================================
# Test
# ==========================================================

if __name__ == "__main__":

    from src.repository.market_repository import MarketRepository

    repository = MarketRepository()

    print("Loading SPY...\n")

    df = repository.fetch_symbol("SPY")

    calculator = ReturnCalculator()

    features = calculator.calculate_all(df)

    print(features.head(10))

    print("\nNew Columns:\n")

    print(features.columns.tolist())

    print("\nShape:\n")

    print(features.shape)