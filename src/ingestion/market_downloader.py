"""
Market data downloader for the SENTINEL project.

Downloads historical market data from Yahoo Finance and returns
a standardized DataFrame ready for validation and database storage.
"""

from __future__ import annotations

import pandas as pd
import yfinance as yf

from src.utils.config import load_config


class MarketDownloader:
    """
    Downloads historical market data for configured assets.
    """

    def __init__(self) -> None:
        """Load asset configuration."""
        self.assets = load_config("assets.yaml")["assets"]

    def get_all_symbols(self) -> list[str]:
        """
        Return every configured ticker symbol.

        Returns
        -------
        list[str]
            List of all configured market symbols.
        """

        symbols: list[str] = []

        for category in self.assets.values():
            symbols.extend(category)

        return symbols

    def _normalize_dataframe(
        self,
        data: pd.DataFrame,
        symbol: str,
    ) -> pd.DataFrame:
        """
        Convert Yahoo Finance output into SENTINEL's
        standard market data schema.

        Parameters
        ----------
        data : pd.DataFrame
            Raw dataframe returned by yfinance.

        symbol : str
            Market symbol.

        Returns
        -------
        pd.DataFrame
            Normalized dataframe.
        """

        # Flatten MultiIndex columns (newer yfinance versions)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        # Convert index to a column
        data = data.reset_index()

        # Standardize column names
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

        # Add symbol
        data["symbol"] = symbol

        # Keep only required columns
        columns = [
            "trade_date",
            "symbol",
            "open",
            "high",
            "low",
            "close",
            "adjusted_close",
            "volume",
        ]

        data = data[columns]

        # Sort by trade date
        data.sort_values("trade_date", inplace=True)

        # Reset index
        data.reset_index(drop=True, inplace=True)

        # Remove pandas column index name (e.g. "Price")
        data.columns.name = None

        return data

    def download(
        self,
        symbol: str,
        start: str = "2000-01-01",
        interval: str = "1d",
    ) -> pd.DataFrame:
        """
        Download historical market data.

        Parameters
        ----------
        symbol : str
            Market symbol.

        start : str
            Start date.

        interval : str
            Data interval.

        Returns
        -------
        pd.DataFrame
            Standardized market data.
        """

        data = yf.download(
            tickers=symbol,
            start=start,
            interval=interval,
            auto_adjust=False,
            progress=False,
        )

        if data.empty:
            raise ValueError(f"No data returned for {symbol}")

        return self._normalize_dataframe(data, symbol)


if __name__ == "__main__":

    downloader = MarketDownloader()

    print("Configured Assets:")
    print(downloader.get_all_symbols())

    print("\nDownloading SPY...\n")

    spy = downloader.download("SPY")

    print(spy.head())

    print("\nColumns:")
    print(spy.columns.tolist())

    print("\nData Types:")
    print(spy.dtypes)

    print("\nShape:")
    print(spy.shape)