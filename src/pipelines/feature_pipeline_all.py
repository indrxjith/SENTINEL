"""
Feature engineering pipeline for all market assets.
"""

from __future__ import annotations

import time

from src.features.feature_pipeline import FeaturePipeline
from src.repository.market_repository import MarketRepository


class FeaturePipelineAll:
    """
    Runs feature engineering for every asset stored in market_prices.
    """

    def __init__(self):

        self.market_repository = MarketRepository()
        self.pipeline = FeaturePipeline()

    # ---------------------------------------------------------

    def run(self):

        start = time.time()

        print("=" * 60)
        print("SENTINEL FEATURE PIPELINE")
        print("=" * 60)

        # Get every symbol from database
        symbols = self.market_repository.fetch_all()["symbol"].unique()

        total_rows = 0
        success = 0
        failed = 0

        for symbol in symbols:

            print("\n" + "-" * 60)
            print(f"Processing {symbol}")
            print("-" * 60)

            try:

                df = self.pipeline.run(symbol)

                total_rows += len(df)
                success += 1

            except Exception as e:

                failed += 1

                print(f"\n❌ Failed: {symbol}")

                print(e)

        elapsed = time.time() - start

        print("\n")
        print("=" * 60)
        print("PIPELINE SUMMARY")
        print("=" * 60)

        print(f"Assets Processed : {success}")
        print(f"Assets Failed    : {failed}")
        print(f"Rows Engineered  : {total_rows:,}")
        print(f"Execution Time   : {elapsed:.2f} sec")


if __name__ == "__main__":

    FeaturePipelineAll().run()