"""
VaR Backtesting Pipeline for SENTINEL.

Runs the VaR backtesting engine for every configured asset.
"""

from __future__ import annotations

import time

from src.analytics.var_backtest import VarBacktestEngine
from src.ingestion.market_downloader import MarketDownloader


class VarBacktestPipeline:
    """
    Executes VaR backtesting for all configured assets.
    """

    def __init__(self):

        self.engine = VarBacktestEngine()

        self.downloader = MarketDownloader()

    # ==========================================================
    # Run One Symbol
    # ==========================================================

    def run_symbol(
        self,
        symbol: str,
    ):

        print("\n" + "=" * 70)
        print(f"Processing {symbol}")
        print("=" * 70)

        start = time.time()

        df = self.engine.run(symbol)

        elapsed = time.time() - start

        print("\n" + "=" * 60)
        print("BACKTEST SUMMARY")
        print("=" * 60)

        print(f"Symbol          : {symbol}")
        print(f"Rows Processed  : {len(df):,}")
        print(f"Execution Time  : {elapsed:.2f} sec")

        return df

    # ==========================================================
    # Run All Symbols
    # ==========================================================

    def run_all(self):

        print("=" * 70)
        print("SENTINEL VAR BACKTEST PIPELINE")
        print("=" * 70)

        start = time.time()

        symbols = self.downloader.get_all_symbols()

        assets = 0
        rows = 0

        for symbol in symbols:

            df = self.run_symbol(symbol)

            assets += 1
            rows += len(df)

        elapsed = time.time() - start

        print("\n" + "=" * 70)
        print("VAR BACKTEST PIPELINE COMPLETE")
        print("=" * 70)

        print(f"Assets Processed : {assets}")
        print(f"Rows Processed   : {rows:,}")
        print(f"Execution Time   : {elapsed:.2f} sec")


# ==========================================================
# Test
# ==========================================================

if __name__ == "__main__":

    pipeline = VarBacktestPipeline()

    pipeline.run_all()