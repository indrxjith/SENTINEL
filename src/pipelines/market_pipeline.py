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

            print(f"\nDownloading {symbol}...")

            try:

                df = self.downloader.download(symbol)

                report = self.validator.validate(df)

                if report.is_valid:

                    inserted = self.repository.insert(df)

                    rows_inserted += inserted
                    assets_processed += 1

                    print(f"✓ {inserted:,} rows inserted.")

                else:

                    assets_failed += 1

                    print(report.summary())

            except Exception as e:

                assets_failed += 1

                print(f"✗ {symbol} failed")
                print(e)

        elapsed = time.time() - start

        print("\n" + "=" * 60)
        print("PIPELINE SUMMARY")
        print("=" * 60)

        print(f"Assets processed : {assets_processed}")
        print(f"Assets failed    : {assets_failed}")
        print(f"Rows inserted    : {rows_inserted:,}")
        print(f"Elapsed time     : {elapsed:.2f} seconds")


if __name__ == "__main__":

    pipeline = MarketPipeline()

    pipeline.run()