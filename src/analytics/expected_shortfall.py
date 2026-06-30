"""
Expected Shortfall (CVaR) Engine for SENTINEL.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.repository.feature_repository import FeatureRepository


class ExpectedShortfallEngine:
    """
    Computes rolling Historical Expected Shortfall (CVaR).
    """

    WINDOW = 252

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
    # Rolling Expected Shortfall
    # ==========================================================

    @staticmethod
    def rolling_expected_shortfall(
        returns: pd.Series,
        confidence: float,
        window: int,
    ) -> pd.Series:
        """
        Historical Expected Shortfall (CVaR).

        Computes the average loss below the rolling VaR threshold.
        """

        alpha = 1.0 - confidence

        def calculate(window_returns):

            var = np.quantile(window_returns, alpha)

            tail = window_returns[window_returns <= var]

            if len(tail) == 0:
                return np.nan

            return tail.mean()

        return returns.rolling(window).apply(
            calculate,
            raw=True,
        )

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

        result["expected_shortfall_95"] = (
            self.rolling_expected_shortfall(
                returns,
                confidence=0.95,
                window=self.WINDOW,
            )
        )

        result["expected_shortfall_99"] = (
            self.rolling_expected_shortfall(
                returns,
                confidence=0.99,
                window=self.WINDOW,
            )
        )

        return result


# ==========================================================
# Test
# ==========================================================

if __name__ == "__main__":

    engine = ExpectedShortfallEngine()

    es = engine.calculate("SPY")

    print("=" * 60)
    print("SENTINEL EXPECTED SHORTFALL ENGINE")
    print("=" * 60)

    print()

    print(es.tail())

    print()

    print(es.describe())