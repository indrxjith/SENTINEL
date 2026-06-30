"""
Base feature engineering class.

Provides common functionality for all feature
engineering modules.
"""

from __future__ import annotations

import pandas as pd


class BaseFeatureEngineer:
    """
    Base class for all feature engineering modules.
    """

    REQUIRED_COLUMNS = [
        "trade_date",
        "symbol",
        "adjusted_close",
    ]

    def prepare_data(
        self,
        data: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Validate and prepare dataframe.
        """

        missing = [
            column
            for column in self.REQUIRED_COLUMNS
            if column not in data.columns
        ]

        if missing:
            raise ValueError(
                f"Missing required columns: {missing}"
            )

        data = data.copy()

        data.sort_values(
            "trade_date",
            inplace=True,
        )

        data.reset_index(
            drop=True,
            inplace=True,
        )

        return data
    
    # ==========================================================
# Test
# ==========================================================

if __name__ == "__main__":

    from src.repository.market_repository import MarketRepository

    repository = MarketRepository()

    print("Loading SPY from PostgreSQL...\n")

    df = repository.fetch_symbol("SPY")

    engineer = BaseFeatureEngineer()

    prepared = engineer.prepare_data(df)

    print(prepared.head())

    print("\nColumns:")
    print(prepared.columns.tolist())

    print("\nShape:")
    print(prepared.shape)