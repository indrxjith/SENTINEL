"""
Risk Score Engine for SENTINEL.
"""

from __future__ import annotations

import pandas as pd

from src.repository.feature_repository import FeatureRepository
from src.repository.beta_repository import BetaRepository
from src.repository.var_repository import VarRepository
from src.repository.expected_shortfall_repository import (
    ExpectedShortfallRepository,
)
from src.repository.regime_repository import RegimeRepository


class RiskScoreEngine:
    """
    Computes a unified market risk score using
    market features, beta, VaR, expected shortfall,
    and market regimes.
    """

    def __init__(self):

        self.feature_repository = FeatureRepository()

        self.beta_repository = BetaRepository()

        self.var_repository = VarRepository()

        self.expected_shortfall_repository = (
            ExpectedShortfallRepository()
        )

        self.regime_repository = RegimeRepository()

    # ==========================================================
    # Load Data
    # ==========================================================

    def load_features(self, symbol):

        return self.feature_repository.fetch_symbol(symbol)

    def load_beta(self, symbol):

        return self.beta_repository.fetch_symbol(symbol)

    def load_var(self, symbol):

        return self.var_repository.fetch_symbol(symbol)

    def load_expected_shortfall(self, symbol):

        return self.expected_shortfall_repository.fetch_symbol(symbol)

    def load_regimes(self, symbol):

        return self.regime_repository.fetch_symbol(symbol)

    # ==========================================================
    # Merge
    # ==========================================================

    def merge_data(self, symbol):

        features = self.load_features(symbol)

        beta = self.load_beta(symbol)

        var = self.load_var(symbol)

        es = self.load_expected_shortfall(symbol)

        regimes = self.load_regimes(symbol)

        df = features.merge(

            beta[
                [
                    "trade_date",
                    "beta_252",
                ]
            ],

            on="trade_date",

            how="left",

        )

        df = df.merge(

            var[
                [
                    "trade_date",
                    "historical_var_95",
                ]
            ],

            on="trade_date",

            how="left",

        )

        df = df.merge(

            es[
                [
                    "trade_date",
                    "expected_shortfall_95",
                ]
            ],

            on="trade_date",

            how="left",

        )

        df = df.merge(

            regimes[
                [
                    "trade_date",
                    "risk_regime",
                ]
            ],

            on="trade_date",

            how="left",

        )

        # Benchmark beta

        df["beta_252"] = df["beta_252"].fillna(1.0)

        return df

    # ==========================================================
    # Volatility Score
    # ==========================================================

    @staticmethod
    def volatility_score(vol):

        if pd.isna(vol):
            return None

        if vol < 0.15:
            return 10

        if vol < 0.25:
            return 30

        if vol < 0.40:
            return 60

        return 100

    # ==========================================================
    # Drawdown Score
    # ==========================================================

    @staticmethod
    def drawdown_score(drawdown):

        if pd.isna(drawdown):
            return None

        if drawdown > -0.05:
            return 10

        if drawdown > -0.15:
            return 40

        if drawdown > -0.30:
            return 70

        return 100

    # ==========================================================
    # Beta Score
    # ==========================================================

    @staticmethod
    def beta_score(beta):

        if pd.isna(beta):
            return None

        if beta < 0.8:
            return 20

        if beta < 1.2:
            return 40

        if beta < 1.5:
            return 70

        return 100

    # ==========================================================
    # Historical VaR Score
    # ==========================================================

    @staticmethod
    def var_score(var95):

        if pd.isna(var95):
            return None

        if var95 > -0.02:
            return 20

        if var95 > -0.04:
            return 50

        return 100

    # ==========================================================
    # Expected Shortfall Score
    # ==========================================================

    @staticmethod
    def expected_shortfall_score(es95):

        if pd.isna(es95):
            return None

        if es95 > -0.03:
            return 20

        if es95 > -0.05:
            return 60

        return 100


    # ==========================================================
    # Overall Score
    # ==========================================================

    @staticmethod
    def total_score(row):

        return round(

            (
                row["volatility_score"] * 0.25
                + row["drawdown_score"] * 0.20
                + row["beta_score"] * 0.15
                + row["var_score"] * 0.20
                + row["expected_shortfall_score"] * 0.20
            ),

            2,

        )

    # ==========================================================
    # Risk Level
    # ==========================================================

    @staticmethod
    def risk_level(score):

        if pd.isna(score):
            return None

        if score <= 30:
            return "LOW"

        if score <= 60:
            return "MODERATE"

        if score <= 80:
            return "HIGH"

        return "EXTREME"

    # ==========================================================
    # Calculate
    # ==========================================================

    def calculate(
        self,
        symbol: str,
    ) -> pd.DataFrame:

        df = self.merge_data(symbol)

        df["volatility_score"] = df[
            "annualized_volatility_20d"
        ].apply(self.volatility_score)

        df["drawdown_score"] = df[
            "drawdown"
        ].apply(self.drawdown_score)

        df["beta_score"] = df[
            "beta_252"
        ].apply(self.beta_score)

        df["var_score"] = df[
            "historical_var_95"
        ].apply(self.var_score)

        df["expected_shortfall_score"] = df[
            "expected_shortfall_95"
        ].apply(self.expected_shortfall_score)

        # Remove rows where indicators are unavailable
        df = df.dropna(
            subset=[
                "volatility_score",
                "drawdown_score",
                "beta_score",
                "var_score",
                "expected_shortfall_score",
            ]
        )

        df["total_score"] = df.apply(
            self.total_score,
            axis=1,
        )

        df["risk_level"] = df[
            "total_score"
        ].apply(self.risk_level)

        return df[
            [
                "trade_date",
                "symbol",
                "volatility_score",
                "drawdown_score",
                "beta_score",
                "var_score",
                "expected_shortfall_score",
                "total_score",
                "risk_level",
            ]
        ]


# ==========================================================
# Test
# ==========================================================

if __name__ == "__main__":

    engine = RiskScoreEngine()

    scores = engine.calculate("SPY")

    print("=" * 60)
    print("SENTINEL RISK SCORE ENGINE")
    print("=" * 60)

    print()

    print(scores.tail())

    print()

    print(scores["risk_level"].value_counts())

    print()

    print(scores["total_score"].describe())        