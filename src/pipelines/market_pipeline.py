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

                    # ----------------------------------------------
                    # Try to salvage the load by dropping exactly
                    # the offending rows (e.g. an incomplete
                    # trailing bar with a NaN close), then
                    # re-validating what's left. Structural
                    # problems (missing columns, empty frame,
                    # duplicate rows, bad dtypes) can't be fixed
                    # this way and will still fail re-validation.
                    # ----------------------------------------------

                    before = len(df)

                    bad_row_mask = self.validator.identify_bad_rows(df)
                    removed = int(bad_row_mask.sum())

                    if removed:

                        print(f"\nDropping {removed} bad row(s):")
                        print(
                            df.loc[
                                bad_row_mask,
                                [
                                    "trade_date",
                                    "symbol",
                                    "open",
                                    "high",
                                    "low",
                                    "close",
                                    "adjusted_close",
                                    "volume",
                                ],
                            ].to_string(index=False)
                        )

                    df = df.loc[~bad_row_mask].copy()

                    retry_report = self.validator.validate(df)

                    if not retry_report.is_valid:

                        print("\n" + retry_report.summary())

                        assets_failed += 1

                        print(
                            "\nSkipping because of critical validation "
                            "errors that could not be resolved by "
                            "dropping individual rows."
                        )

                        continue

                    print(
                        f"\nRemoved {removed} invalid row(s) "
                        f"({before:,} -> {len(df):,})."
                    )
                    print(f"Continuing with {len(df):,} valid rows...")

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