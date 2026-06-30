"""
Market data ingestion pipeline for SENTINEL.
"""

from __future__ import annotations

import time

from src.ingestion.market_downloader import MarketDownloader
from src.repository.market_repository import MarketRepository
from src.validation.data_validator import DataValidator


class MarketPipeline:
    """
    End-to-end market data ingestion pipeline.
    """

    def __init__(self):

        self.downloader = MarketDownloader()
        self.validator = DataValidator()
        self.repository = MarketRepository()

    # ==========================================================
    # Run Pipeline
    # ==========================================================

    def run(self):

        start = time.time()

        symbols = self.downloader.get_all_symbols()

        assets_processed = 0
        assets_failed = 0
        rows_inserted = 0

        print("=" * 60)
        print("SENTINEL MARKET INGESTION PIPELINE")
        print("=" * 60)

        for symbol in symbols:

            print(f"\nProcessing {symbol}...")

            try:

                # --------------------------------------------------
                # Download latest data
                # --------------------------------------------------

                df = self.downloader.download(symbol)

                # --------------------------------------------------
                # Validate
                # --------------------------------------------------

                report = self.validator.validate(df)

                if not report.is_valid:

                    print(report.summary())

                    # If there are errors OTHER than OHLC,
                    # skip this symbol.
                    non_ohlc_errors = [
                        error
                        for error in report.errors
                        if "OHLC" not in error
                    ]

                    if non_ohlc_errors:

                        assets_failed += 1

                        print(
                            "\nSkipping because of critical validation errors."
                        )

                        continue

                    # ----------------------------------------------
                    # Remove invalid OHLC rows only
                    # ----------------------------------------------

                    before = len(df)

                    df = df[
                        (df["high"] >= df["low"])
                        & (df["high"] >= df["open"])
                        & (df["high"] >= df["close"])
                        & (df["low"] <= df["open"])
                        & (df["low"] <= df["close"])
                    ].copy()

                    removed = before - len(df)

                    print(
                        f"\nRemoved {removed} invalid OHLC row(s)."
                    )

                    print(
                        f"Continuing with {len(df):,} valid rows..."
                    )

                # --------------------------------------------------
                # Refresh database
                # --------------------------------------------------

                deleted = self.repository.delete_symbol(symbol)

                if deleted > 0:

                    print(
                        f"Deleted {deleted:,} existing rows"
                    )

                inserted = self.repository.insert(df)

                rows_inserted += inserted
                assets_processed += 1

                print(f"✓ {inserted:,} rows inserted")

            except Exception as e:

                assets_failed += 1

                print(f"✗ {symbol} failed")

                print(e)

        elapsed = time.time() - start

        print("\n" + "=" * 60)
        print("PIPELINE SUMMARY")
        print("=" * 60)

        print(f"Assets Processed : {assets_processed}")
        print(f"Assets Failed    : {assets_failed}")
        print(f"Rows Inserted    : {rows_inserted:,}")
        print(f"Execution Time   : {elapsed:.2f} sec")


# ==========================================================
# Test
# ==========================================================

if __name__ == "__main__":

    pipeline = MarketPipeline()

    pipeline.run()