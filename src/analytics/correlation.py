"""
Rolling Correlation Engine for SENTINEL.
"""

from __future__ import annotations

import itertools

import pandas as pd

from src.repository.feature_repository import FeatureRepository


class CorrelationEngine:
    """
    Computes rolling correlations between all assets.
    """

    def __init__(self):

        self.repository = FeatureRepository()

    # ==========================================================
    # Load Data
    # ==========================================================

    def load_data(self) -> pd.DataFrame:

        return self.repository.fetch_all()

    # ==========================================================
    # Build Return Matrix
    # ==========================================================

    def build_return_matrix(
        self,
        df: pd.DataFrame,
    ) -> pd.DataFrame:

        matrix = df.pivot_table(
            index="trade_date",
            columns="symbol",
            values="simple_return",
        )

        matrix = matrix.sort_index()

        return matrix

    # ==========================================================
    # Asset Pairs
    # ==========================================================

    @staticmethod
    def asset_pairs(
        matrix: pd.DataFrame,
    ):

        return list(
            itertools.combinations(
                matrix.columns,
                2,
            )
        )

    # ==========================================================
    # Rolling Correlation
    # ==========================================================

    @staticmethod
    def rolling_corr(
        series1: pd.Series,
        series2: pd.Series,
        window: int,
    ) -> pd.Series:

        return series1.rolling(window).corr(series2)

    # ==========================================================
    # Calculate
    # ==========================================================

    def calculate(self) -> pd.DataFrame:

        print("=" * 60)
        print("SENTINEL ROLLING CORRELATION ENGINE")
        print("=" * 60)

        print("\nLoading engineered features...")

        df = self.load_data()

        print(f"✓ {len(df):,} rows loaded")

        print("\nBuilding return matrix...")

        matrix = self.build_return_matrix(df)

        print(f"✓ Matrix Shape : {matrix.shape}")

        print("\nGenerating asset pairs...")

        pairs = self.asset_pairs(matrix)

        print(f"✓ {len(pairs)} pairs")

        print("\nCalculating rolling correlations...")

        rows = []

        for asset_1, asset_2 in pairs:

            corr20 = self.rolling_corr(
                matrix[asset_1],
                matrix[asset_2],
                20,
            )

            corr60 = self.rolling_corr(
                matrix[asset_1],
                matrix[asset_2],
                60,
            )

            corr252 = self.rolling_corr(
                matrix[asset_1],
                matrix[asset_2],
                252,
            )

            temp = pd.DataFrame(
                {
                    "trade_date": matrix.index,
                    "asset_1": asset_1,
                    "asset_2": asset_2,
                    "rolling_corr_20": corr20.values,
                    "rolling_corr_60": corr60.values,
                    "rolling_corr_252": corr252.values,
                }
            )

            rows.append(temp)

        correlations = pd.concat(
            rows,
            ignore_index=True,
        )

        print(
            f"✓ Generated {len(correlations):,} raw rows"
        )

        print("\nRemoving incomplete windows...")

        correlations = correlations.dropna(
            subset=[
                "rolling_corr_20",
                "rolling_corr_60",
                "rolling_corr_252",
            ]
        )

        correlations = correlations.sort_values(
            [
                "trade_date",
                "asset_1",
                "asset_2",
            ]
        ).reset_index(drop=True)

        print(
            f"✓ Final rows: {len(correlations):,}"
        )

        return correlations


# ==========================================================
# Test
# ==========================================================

if __name__ == "__main__":

    engine = CorrelationEngine()

    correlations = engine.calculate()

    print()

    print("=" * 60)
    print("LAST 10 ROWS")
    print("=" * 60)

    print(correlations.tail(10))

    print()

    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)

    print(correlations.describe())
