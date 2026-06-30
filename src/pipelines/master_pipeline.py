"""
Master Pipeline for SENTINEL.

Runs the complete analytics workflow.
"""

from __future__ import annotations

import time

from src.pipelines.market_pipeline import MarketPipeline
from src.pipelines.feature_pipeline import FeaturePipeline
from src.pipelines.correlation_pipeline import CorrelationPipeline
from src.pipelines.beta_pipeline import BetaPipeline
from src.pipelines.var_pipeline import VarPipeline
from src.pipelines.expected_shortfall_pipeline import (
    ExpectedShortfallPipeline,
)
from src.pipelines.regime_pipeline import RegimePipeline
from src.pipelines.risk_score_pipeline import RiskScorePipeline


class MasterPipeline:
    """
    Executes every SENTINEL pipeline in the correct order.
    """

    def __init__(self):

        self.market_pipeline = MarketPipeline()

        self.feature_pipeline = FeaturePipeline()

        self.correlation_pipeline = CorrelationPipeline()

        self.beta_pipeline = BetaPipeline()

        self.var_pipeline = VarPipeline()

        self.expected_shortfall_pipeline = (
            ExpectedShortfallPipeline()
        )

        self.regime_pipeline = RegimePipeline()

        self.risk_score_pipeline = RiskScorePipeline()

    # ==========================================================
    # Run
    # ==========================================================

    def run(self):

        start = time.time()

        print("=" * 70)
        print("SENTINEL MASTER PIPELINE")
        print("=" * 70)

        # ------------------------------------------------------

        print("\n[1/8] MARKET PIPELINE")
        self.market_pipeline.run()

        # ------------------------------------------------------

        print("\n[2/8] FEATURE PIPELINE")
        self.feature_pipeline.run_all()

        # ------------------------------------------------------

        print("\n[3/8] CORRELATION PIPELINE")
        self.correlation_pipeline.run()

        # ------------------------------------------------------

        print("\n[4/8] BETA PIPELINE")
        self.beta_pipeline.run()

        # ------------------------------------------------------

        print("\n[5/8] VAR PIPELINE")
        self.var_pipeline.run()

        # ------------------------------------------------------

        print("\n[6/8] EXPECTED SHORTFALL PIPELINE")
        self.expected_shortfall_pipeline.run()

        # ------------------------------------------------------

        print("\n[7/8] REGIME PIPELINE")
        self.regime_pipeline.run()

        # ------------------------------------------------------

        print("\n[8/8] RISK SCORE PIPELINE")
        self.risk_score_pipeline.run()

        # ------------------------------------------------------

        elapsed = time.time() - start

        print("\n" + "=" * 70)
        print("SENTINEL MASTER PIPELINE COMPLETED")
        print("=" * 70)

        print(f"Execution Time : {elapsed:.2f} seconds")


# ==========================================================
# Test
# ==========================================================

if __name__ == "__main__":

    pipeline = MasterPipeline()

    pipeline.run()