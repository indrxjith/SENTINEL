"""
Market Regime Engine for SENTINEL.
"""

from __future__ import annotations

import pandas as pd

from src.repository.feature_repository import FeatureRepository
from src.repository.beta_repository import BetaRepository
from src.repository.var_repository import VarRepository
from src.repository.expected_shortfall_repository import (
    ExpectedShortfallRepository,
)


class RegimeEngine:

    def __init__(self):

        self.feature_repository = FeatureRepository()
        self.beta_repository = BetaRepository()
        self.var_repository = VarRepository()
        self.expected_shortfall_repository = (
            ExpectedShortfallRepository()
        )

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

    # ==========================================================
    # Merge
    # ==========================================================

    def merge_data(self, symbol):

        features = self.load_features(symbol)

        beta = self.load_beta(symbol)

        var = self.load_var(symbol)

        es = self.load_expected_shortfall(symbol)

        df = features.merge(

            beta[["trade_date", "beta_252"]],

            on="trade_date",

            how="left",

        )

        df = df.merge(

            var[["trade_date", "historical_var_95"]],

            on="trade_date",

            how="left",

        )

        df = df.merge(

            es[["trade_date", "expected_shortfall_95"]],

            on="trade_date",

            how="left",

        )

        # Benchmark beta

        df["beta_252"] = df["beta_252"].fillna(1.0)

        return df

    # ==========================================================
    # Regime Classifiers
    # ==========================================================

    @staticmethod
    def volatility_regime(vol):

        if pd.isna(vol):
            return None

        if vol < 0.15:
            return "LOW"

        elif vol < 0.30:
            return "NORMAL"

        return "HIGH"

    @staticmethod
    def trend_regime(close, sma200):

        if pd.isna(sma200):
            return None

        if close > sma200:
            return "BULL"

        return "BEAR"

    @staticmethod
    def drawdown_regime(drawdown):

        if pd.isna(drawdown):
            return None

        if drawdown > -0.05:
            return "HEALTHY"

        elif drawdown > -0.15:
            return "CORRECTION"

        return "CRISIS"

    @staticmethod
    def risk_regime(var95):

        if pd.isna(var95):
            return None

        if var95 > -0.02:
            return "LOW"

        elif var95 > -0.04:
            return "MEDIUM"

        return "HIGH"

    # ==========================================================
    # Calculate
    # ==========================================================

    def calculate(self, symbol):

        df = self.merge_data(symbol)

        df["volatility_regime"] = df[
            "annualized_volatility_20d"
        ].apply(self.volatility_regime)


        df["trend_regime"] = df.apply(

    lambda row: self.trend_regime(

        row["ema_20"],

        row["sma_200"],

    ),

    axis=1,

    )

        df["drawdown_regime"] = df[
            "drawdown"
        ].apply(self.drawdown_regime)

        df["risk_regime"] = df[
            "historical_var_95"
        ].apply(self.risk_regime)

        return df[
            [

                "trade_date",

                "symbol",

                "volatility_regime",

                "trend_regime",

                "drawdown_regime",

                "risk_regime",

            ]
        ]


# ==========================================================
# Test
# ==========================================================

if __name__ == "__main__":

    engine = RegimeEngine()

    regimes = engine.calculate("SPY")

    print("=" * 60)
    print("SENTINEL MARKET REGIME ENGINE")
    print("=" * 60)

    print()

    print(regimes.tail())

    print()

    print(regimes["risk_regime"].value_counts())

    print()

    print(regimes["trend_regime"].value_counts())