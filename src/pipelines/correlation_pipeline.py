"""
Correlation Pipeline for SENTINEL.
"""

from __future__ import annotations

import time

from src.analytics.correlation import CorrelationEngine
from src.repository.correlation_repository import CorrelationRepository


class CorrelationPipeline:
    """
    Computes and stores rolling correlations.
    """

    def __init__(self):

        self.engine = CorrelationEngine()

        self.repository = CorrelationRepository()

    # ==========================================================
    # Run Pipeline
    # ==========================================================

    def run(self):

        start = time.time()

        print("=" * 60)
        print("SENTINEL CORRELATION PIPELINE")
        print("=" * 60)

        # ------------------------------------------------------

        print("\nCalculating rolling correlations...")

        df = self.engine.calculate()

        print(f"✓ {len(df):,} correlation rows calculated")

        # ------------------------------------------------------

        print("\nRefreshing database...")

        self.repository.delete_all()

        inserted = self.repository.insert(df)

        # ------------------------------------------------------

        elapsed = time.time() - start

        print("\n" + "=" * 60)
        print("PIPELINE SUMMARY")
        print("=" * 60)

        print(f"Rows Saved      : {inserted:,}")
        print(f"Execution Time  : {elapsed:.2f} sec")


# ==========================================================
# Test
# ==========================================================

if __name__ == "__main__":

    pipeline = CorrelationPipeline()

    pipeline.run()