"""
Market repository for the SENTINEL project.

Handles all PostgreSQL operations for market data.
"""

from __future__ import annotations

import pandas as pd
from sqlalchemy import text

from src.utils.database import engine


class MarketRepository:
    """
    Repository responsible for reading and writing
    market data to PostgreSQL.
    """

    TABLE_NAME = "sentinel.market_prices"

    def insert(self, data: pd.DataFrame) -> int:
        """
        Insert market data into PostgreSQL.

        Returns
        -------
        int
            Number of inserted rows.
        """

        data.to_sql(
            name="market_prices",
            schema="sentinel",
            con=engine,
            if_exists="append",
            index=False,
            method="multi",
            chunksize=1000,
        )

        return len(data)

    # -----------------------------------------------------

    def fetch_symbol(self, symbol: str) -> pd.DataFrame:
        """
        Fetch all rows for a single market symbol.
        """

        query = text(
            """
            SELECT *
            FROM sentinel.market_prices
            WHERE symbol = :symbol
            ORDER BY trade_date;
            """
        )

        return pd.read_sql(
            query,
            engine,
            params={"symbol": symbol},
        )

    # -----------------------------------------------------

    def fetch_all(self) -> pd.DataFrame:
        """
        Fetch all market data.
        """

        query = text(
            """
            SELECT *
            FROM sentinel.market_prices
            ORDER BY symbol, trade_date;
            """
        )

        return pd.read_sql(query, engine)

    # -----------------------------------------------------

    def latest_date(self, symbol: str):
        """
        Return latest stored trading date.
        """

        query = text(
            """
            SELECT MAX(trade_date)
            FROM sentinel.market_prices
            WHERE symbol = :symbol;
            """
        )

        with engine.connect() as conn:

            return conn.execute(
                query,
                {"symbol": symbol},
            ).scalar()

    # -----------------------------------------------------

    def delete_symbol(self, symbol: str) -> int:
        """
        Delete all rows for one symbol.

        Returns
        -------
        int
            Number of deleted rows.
        """

        query = text(
            """
            DELETE
            FROM sentinel.market_prices
            WHERE symbol = :symbol;
            """
        )

        with engine.begin() as conn:

            result = conn.execute(
                query,
                {"symbol": symbol},
            )

        return result.rowcount

    # -----------------------------------------------------

    def row_count(self) -> int:
        """
        Return total row count.
        """

        query = text(
            """
            SELECT COUNT(*)
            FROM sentinel.market_prices;
            """
        )

        with engine.connect() as conn:

            return conn.execute(query).scalar()


# ==========================================================
# Test
# ==========================================================

if __name__ == "__main__":

    from src.ingestion.market_downloader import MarketDownloader
    from src.validation.data_validator import DataValidator

    print("\nDownloading SPY...\n")

    downloader = MarketDownloader()
    validator = DataValidator()
    repository = MarketRepository()

    df = downloader.download("SPY")

    report = validator.validate(df)

    print(report.summary())

    if report.is_valid:

        inserted = repository.insert(df)

        print(f"\n✅ Inserted {inserted:,} rows.")

        print(f"\nRows in database: {repository.row_count():,}")

        print("\nLatest SPY date:")

        print(repository.latest_date("SPY"))

    else:

        print("\nValidation failed.")