"""
Correlation Engine for SENTINEL.
"""

from __future__ import annotations

import pandas as pd

from src.repository.feature_repository import FeatureRepository


class CorrelationEngine:
    """
    Computes correlation statistics from engineered features.
    """

    def __init__(self):

        self.repository = FeatureRepository()

    # ==========================================================
    # Load Data
    # ==========================================================

    def load_data(self) -> pd.DataFrame:

        return self.repository.fetch_all()

    # ==========================================================
    # Return Matrix
    # ==========================================================

    def build_return_matrix(
        self,
        df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Creates a pivot table:
            rows    -> trade_date
            columns -> symbol
            values  -> simple_return
        """

        matrix = df.pivot_table(
            index="trade_date",
            columns="symbol",
            values="simple_return",
        )

        return matrix.sort_index()

    # ==========================================================
    # Static Correlation
    # ==========================================================

    def correlation_matrix(
        self,
        matrix: pd.DataFrame,
    ) -> pd.DataFrame:

        return matrix.corr()

    # ==========================================================
    # Test
    # ==========================================================

    def run(self):

        print("=" * 60)
        print("SENTINEL CORRELATION ENGINE")
        print("=" * 60)

        print("\nLoading engineered features...")

        df = self.load_data()

        print(f"✓ {len(df):,} rows loaded")

        print("\nBuilding return matrix...")

        matrix = self.build_return_matrix(df)

        print(f"✓ Shape: {matrix.shape}")

        print("\nCalculating correlation matrix...")

        corr = self.correlation_matrix(matrix)

        print("\nCorrelation Matrix\n")

        print(corr.round(3))

        return corr


if __name__ == "__main__":

    CorrelationEngine().run()