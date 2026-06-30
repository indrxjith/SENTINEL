"""
Feature engineering pipeline for SENTINEL.
"""

from __future__ import annotations

import time
import pandas as pd

from src.repository.market_repository import MarketRepository
from src.repository.feature_repository import FeatureRepository

from src.features.returns import ReturnCalculator
from src.features.volatility import VolatilityCalculator
from src.features.drawdown import DrawdownCalculator
from src.features.trend import TrendCalculator


class FeaturePipeline:
    """
    End-to-end feature engineering pipeline.
    """

    def __init__(self):

        self.market_repository = MarketRepository()
        self.feature_repository = FeatureRepository()

        self.return_calculator = ReturnCalculator()
        self.volatility_calculator = VolatilityCalculator()
        self.drawdown_calculator = DrawdownCalculator()
        self.trend_calculator = TrendCalculator()

    # ==========================================================
    # Run Pipeline
    # ==========================================================

    def run(self, symbol: str) -> pd.DataFrame:

        start = time.time()

        print("=" * 60)
        print("SENTINEL FEATURE ENGINEERING PIPELINE")
        print("=" * 60)

        # ------------------------------------------------------

        print(f"\nLoading {symbol} from PostgreSQL...")

        df = self.market_repository.fetch_symbol(symbol)

        print(f"✓ Loaded {len(df):,} rows")

        # ------------------------------------------------------

        print("\nCalculating return features...")

        df = self.return_calculator.calculate_all(df)

        print("✓ Returns completed")

        # ------------------------------------------------------

        print("\nCalculating volatility features...")

        df = self.volatility_calculator.calculate(df)

        print("✓ Volatility completed")

        # ------------------------------------------------------

        print("\nCalculating drawdown features...")

        df = self.drawdown_calculator.calculate(df)

        print("✓ Drawdown completed")

        # ------------------------------------------------------

        print("\nCalculating trend features...")

        df = self.trend_calculator.calculate(df)

        print("✓ Trend completed")

        # ------------------------------------------------------
        # Save to PostgreSQL
        # ------------------------------------------------------

        print("\nSaving engineered features...")

        # Remove old rows for this symbol
        self.feature_repository.delete_symbol(symbol)

        # Save ALL engineered features
        inserted = self.feature_repository.insert(df)

        print(f"✓ {inserted:,} rows saved")

        # ------------------------------------------------------

        elapsed = time.time() - start

        print("\n" + "=" * 60)
        print("PIPELINE SUMMARY")
        print("=" * 60)

        print(f"Symbol          : {symbol}")
        print(f"Rows Processed  : {len(df):,}")
        print(f"Columns         : {len(df.columns)}")
        print(f"Rows Saved      : {inserted:,}")
        print(f"Execution Time  : {elapsed:.2f} sec")

        return df


# ==========================================================
# Test
# ==========================================================

if __name__ == "__main__":

    pipeline = FeaturePipeline()

    features = pipeline.run("SPY")

    print("\nLast 5 rows:\n")

    print(features.tail())

    print("\n")

    print("=" * 60)
    print("ENGINEERED FEATURES")
    print("=" * 60)

    feature_columns = [

        column

        for column in features.columns

        if column not in [

            "id",
            "symbol",
            "trade_date",
            "open",
            "high",
            "low",
            "close",
            "adjusted_close",
            "volume",
            "created_at",
        ]
    ]

    print(f"\nTotal Engineered Features: {len(feature_columns)}\n")

    for column in feature_columns:
        print(column)

    print("\n")

    print("Rows currently in market_features:")

    print(pipeline.feature_repository.row_count())