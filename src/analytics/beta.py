"""
Rolling Beta Engine for SENTINEL.
"""

from __future__ import annotations

import pandas as pd

from src.analytics.statistics import RollingStatistics
from src.repository.feature_repository import FeatureRepository


class BetaEngine:
    """
    Computes rolling beta against a benchmark.
    """

    def __init__(self):

        self.repository = FeatureRepository()

    # ==========================================================
    # Load Returns Matrix
    # ==========================================================

    def load_returns(self) -> pd.DataFrame:

        df = self.repository.fetch_all()

        matrix = (
            df.pivot_table(
                index="trade_date",
                columns="symbol",
                values="simple_return",
            )
            .sort_index()
        )

        return matrix

    # ==========================================================
    # Compute One Beta Series
    # ==========================================================

    def compute_beta(
        self,
        asset_returns: pd.Series,
        benchmark_returns: pd.Series,
        window: int,
    ) -> pd.Series:

        covariance = RollingStatistics.rolling_covariance(
            asset_returns,
            benchmark_returns,
            window,
        )

        variance = RollingStatistics.rolling_variance(
            benchmark_returns,
            window,
        )

        return covariance / variance

    # ==========================================================
    # Build Beta DataFrame
    # ==========================================================

    def calculate(
        self,
        asset: str,
        benchmark: str = "SPY",
    ) -> pd.DataFrame:

        matrix = self.load_returns()

        pair = matrix[[asset, benchmark]].dropna()

        asset_returns = pair[asset]
        benchmark_returns = pair[benchmark]

        result = pd.DataFrame(index=pair.index)

        result["trade_date"] = pair.index
        result["symbol"] = asset
        result["benchmark"] = benchmark

        result["beta_20"] = self.compute_beta(
            asset_returns,
            benchmark_returns,
            20,
        )

        result["beta_60"] = self.compute_beta(
            asset_returns,
            benchmark_returns,
            60,
        )

        result["beta_252"] = self.compute_beta(
            asset_returns,
            benchmark_returns,
            252,
        )

        return result.reset_index(drop=True)


# ==========================================================
# Test
# ==========================================================

if __name__ == "__main__":

    engine = BetaEngine()

    beta = engine.calculate(
        asset="QQQ",
        benchmark="SPY",
    )

    print("=" * 60)
    print("SENTINEL BETA ENGINE")
    print("=" * 60)

    print()

    print(beta.tail())

    print()

    print(beta.describe())