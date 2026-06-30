"""
Value at Risk (VaR) Pipeline for SENTINEL.
"""

from __future__ import annotations

import time

from src.analytics.var import VarEngine
from src.repository.var_repository import VarRepository


class VarPipeline:
    """
    Computes and stores VaR metrics for all assets.
    """

    def __init__(self):

        self.engine = VarEngine()
        self.repository = VarRepository()

        self.symbols = [
            "SPY",
            "QQQ",
            "GLD",
            "USO",
            "BTC-USD",
            "DX-Y.NYB",
            "^TNX",
            "^VIX",
        ]

    # ==========================================================
    # Run Pipeline
    # ==========================================================

    def run(self):

        start = time.time()

        total_rows = 0

        print("=" * 60)
        print("SENTINEL VAR PIPELINE")
        print("=" * 60)

        for symbol in self.symbols:

            print(f"\nProcessing {symbol}...")

            df = self.engine.calculate(symbol)

            self.repository.delete_symbol(symbol)

            inserted = self.repository.insert(df)

            total_rows += inserted

            print(f"✓ {inserted:,} rows saved")

        elapsed = time.time() - start

        print("\n" + "=" * 60)
        print("PIPELINE SUMMARY")
        print("=" * 60)

        print(f"Assets Processed : {len(self.symbols)}")
        print(f"Rows Saved       : {total_rows:,}")
        print(f"Execution Time   : {elapsed:.2f} sec")


# ==========================================================
# Test
# ==========================================================

if __name__ == "__main__":

    pipeline = VarPipeline()

    pipeline.run()