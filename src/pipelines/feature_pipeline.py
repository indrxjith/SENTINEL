"""
Feature engineering pipeline for SENTINEL.
"""

from __future__ import annotations

import time
import pandas as pd

from src.ingestion.market_downloader import MarketDownloader

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

        # Automatically load all supported symbols
        self.symbols = MarketDownloader().get_all_symbols()

    # ==========================================================
    # Run One Symbol
    # ==========================================================

    def run_symbol(
        self,
        symbol: str,
    ) -> pd.DataFrame:

        start = time.time()

        print("=" * 60)
        print("SENTINEL FEATURE ENGINEERING PIPELINE")
        print("=" * 60)

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
        # Save
        # ------------------------------------------------------

        print("\nSaving engineered features...")

        self.feature_repository.delete_symbol(symbol)

        inserted = self.feature_repository.insert(df)

        print(f"✓ {inserted:,} rows saved")

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
    # Run All Symbols
    # ==========================================================

    def run_all(self):

        start = time.time()

        total_rows = 0

        print("=" * 70)
        print("SENTINEL FEATURE PIPELINE")
        print("=" * 70)

        for symbol in self.symbols:

            print("\n" + "=" * 70)
            print(f"Processing {symbol}")
            print("=" * 70)

            df = self.run_symbol(symbol)

            total_rows += len(df)

        elapsed = time.time() - start

        print("\n" + "=" * 70)
        print("FEATURE PIPELINE COMPLETE")
        print("=" * 70)

        print(f"Assets Processed : {len(self.symbols)}")
        print(f"Rows Processed   : {total_rows:,}")
        print(f"Execution Time   : {elapsed:.2f} sec")


# ==========================================================
# Test
# ==========================================================

if __name__ == "__main__":

    pipeline = FeaturePipeline()

    pipeline.run_all()