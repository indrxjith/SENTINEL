"""
Market data downloader for the SENTINEL project.

Downloads historical market data from Yahoo Finance and returns
a standardized DataFrame ready for validation and database storage.
"""

from __future__ import annotations

import time
from datetime import datetime

import pandas as pd
import yfinance as yf

from src.utils.config import load_config


class MarketDownloader:
    """
    Downloads historical market data for configured assets.
    """

    def __init__(self) -> None:

        self.assets = load_config("assets.yaml")["assets"]

    # ==========================================================
    # Symbols
    # ==========================================================

    def get_all_symbols(self) -> list[str]:

        symbols = []

        for category in self.assets.values():

            symbols.extend(category)

        return symbols

    # ==========================================================
    # Normalize
    # ==========================================================

    def _normalize_dataframe(
        self,
        data: pd.DataFrame,
        symbol: str,
    ) -> pd.DataFrame:

        if isinstance(data.columns, pd.MultiIndex):

            data.columns = data.columns.get_level_values(0)

        data = data.reset_index()

        data.rename(
            columns={
                "Date": "trade_date",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Adj Close": "adjusted_close",
                "Volume": "volume",
            },
            inplace=True,
        )

        data["symbol"] = symbol

        data = data[
            [
                "trade_date",
                "symbol",
                "open",
                "high",
                "low",
                "close",
                "adjusted_close",
                "volume",
            ]
        ]

        data.sort_values("trade_date", inplace=True)

        data.reset_index(drop=True, inplace=True)

        data.columns.name = None

        return data

    # ==========================================================
    # Download
    # ==========================================================

    def download(
        self,
        symbol: str,
        start: str = "2000-01-01",
        interval: str = "1d",
    ) -> pd.DataFrame:

        end = datetime.today().strftime("%Y-%m-%d")

        last_exception = None

        for attempt in range(1, 4):

            try:

                print(f"Downloading {symbol} (Attempt {attempt}/3)...")

                data = yf.download(
                    tickers=symbol,
                    start=start,
                    end=end,
                    interval=interval,
                    auto_adjust=False,
                    progress=False,
                    threads=False,
                )

                if data.empty:

                    raise ValueError(
                        f"No data returned for {symbol}"
                    )

                return self._normalize_dataframe(
                    data,
                    symbol,
                )

            except Exception as e:

                last_exception = e

                print(f"Attempt {attempt} failed.")

                if attempt < 3:

                    print("Retrying in 3 seconds...\n")

                    time.sleep(3)

        raise RuntimeError(
            f"Failed to download {symbol} after 3 attempts."
        ) from last_exception


# ==========================================================
# Test
# ==========================================================

if __name__ == "__main__":

    downloader = MarketDownloader()

    print("=" * 60)
    print("SENTINEL MARKET DOWNLOADER")
    print("=" * 60)

    print("\nConfigured Assets:")

    print(downloader.get_all_symbols())

    print("\nDownloading SPY...\n")

    df = downloader.download("SPY")

    print(df.head())

    print("\nRows:", len(df))

    print("\nColumns:")

    print(df.columns.tolist())

    print("\nData Types:")

    print(df.dtypes)