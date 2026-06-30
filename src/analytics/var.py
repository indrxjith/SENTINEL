"""
Value at Risk (VaR) Engine for SENTINEL.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.analytics.statistics import RollingStatistics
from src.repository.feature_repository import FeatureRepository


class VarEngine:
    """
    Computes rolling Historical and Parametric Value at Risk.
    """

    WINDOW = 252

    Z95 = -1.645
    Z99 = -2.326

    def __init__(self):

        self.repository = FeatureRepository()

    # ==========================================================
    # Load Returns
    # ==========================================================

    def load_returns(
        self,
        symbol: str,
    ) -> pd.DataFrame:

        return self.repository.fetch_symbol(symbol)

    # ==========================================================
    # Historical VaR
    # ==========================================================

    @staticmethod
    def historical_var(
        returns: pd.Series,
        confidence: float,
        window: int,
    ) -> pd.Series:

        alpha = 1 - confidence

        return returns.rolling(window).quantile(alpha)

    # ==========================================================
    # Parametric VaR
    # ==========================================================

    @staticmethod
    def parametric_var(
        returns: pd.Series,
        z_score: float,
        window: int,
    ) -> pd.Series:

        mean = RollingStatistics.rolling_mean(
            returns,
            window,
        )

        std = RollingStatistics.rolling_std(
            returns,
            window,
        )

        return mean + z_score * std

    # ==========================================================
    # Calculate
    # ==========================================================

    def calculate(
        self,
        symbol: str,
    ) -> pd.DataFrame:

        df = self.load_returns(symbol)

        returns = df["simple_return"]

        result = pd.DataFrame()

        result["trade_date"] = df["trade_date"]
        result["symbol"] = symbol

        result["historical_var_95"] = self.historical_var(
            returns,
            confidence=0.95,
            window=self.WINDOW,
        )

        result["historical_var_99"] = self.historical_var(
            returns,
            confidence=0.99,
            window=self.WINDOW,
        )

        result["parametric_var_95"] = self.parametric_var(
            returns,
            z_score=self.Z95,
            window=self.WINDOW,
        )

        result["parametric_var_99"] = self.parametric_var(
            returns,
            z_score=self.Z99,
            window=self.WINDOW,
        )

        return result


# ==========================================================
# Test
# ==========================================================

if __name__ == "__main__":

    engine = VarEngine()

    var = engine.calculate("SPY")

    print("=" * 60)
    print("SENTINEL VAR ENGINE")
    print("=" * 60)

    print()

    print(var.tail())

    print()

    print(var.describe())