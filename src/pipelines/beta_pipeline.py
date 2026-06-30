"""
Beta pipeline for SENTINEL.
"""

from __future__ import annotations

import time

from src.analytics.beta import BetaEngine
from src.repository.beta_repository import BetaRepository


class BetaPipeline:
    """
    Computes and stores rolling betas for all assets.
    """

    BENCHMARK = "SPY"

    def __init__(self):

        self.engine = BetaEngine()
        self.repository = BetaRepository()

    # ==========================================================
    # Run
    # ==========================================================

    def run(self):

        start = time.time()

        matrix = self.engine.load_returns()

        symbols = list(matrix.columns)

        # Don't calculate SPY vs SPY
        symbols.remove(self.BENCHMARK)

        total_rows = 0

        print("=" * 60)
        print("SENTINEL BETA PIPELINE")
        print("=" * 60)

        for symbol in symbols:

            print(f"\nProcessing {symbol}...")

            df = self.engine.calculate(
                asset=symbol,
                benchmark=self.BENCHMARK,
            )

            self.repository.delete_symbol(
                symbol,
                self.BENCHMARK,
            )

            inserted = self.repository.insert(df)

            total_rows += inserted

            print(f"✓ {inserted:,} rows saved")

        elapsed = time.time() - start

        print("\n" + "=" * 60)
        print("PIPELINE SUMMARY")
        print("=" * 60)

        print(f"Benchmark        : {self.BENCHMARK}")
        print(f"Assets Processed : {len(symbols)}")
        print(f"Rows Saved       : {total_rows:,}")
        print(f"Execution Time   : {elapsed:.2f} sec")


if __name__ == "__main__":

    BetaPipeline().run()