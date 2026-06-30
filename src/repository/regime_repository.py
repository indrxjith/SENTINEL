"""
Repository for Market Regimes.
"""

from __future__ import annotations

import pandas as pd
from sqlalchemy import text

from src.utils.database import engine


class RegimeRepository:

    TABLE_NAME = "market_regimes"
    SCHEMA = "sentinel"

    # ==========================================================
    # Insert
    # ==========================================================

    def insert(
        self,
        data: pd.DataFrame,
    ) -> int:

        df = data.copy()

        df = df.drop(
            columns=["id", "created_at"],
            errors="ignore",
        )

        df.to_sql(
            self.TABLE_NAME,
            engine,
            schema=self.SCHEMA,
            if_exists="append",
            index=False,
            method="multi",
        )

        return len(df)

    # ==========================================================
    # Fetch Symbol
    # ==========================================================

    def fetch_symbol(
        self,
        symbol: str,
    ) -> pd.DataFrame:

        query = text(
            """
            SELECT *
            FROM sentinel.market_regimes
            WHERE symbol=:symbol
            ORDER BY trade_date
            """
        )

        return pd.read_sql(
            query,
            engine,
            params={"symbol": symbol},
        )

    # ==========================================================
    # Delete Symbol
    # ==========================================================

    def delete_symbol(
        self,
        symbol: str,
    ):

        query = text(
            """
            DELETE
            FROM sentinel.market_regimes
            WHERE symbol=:symbol
            """
        )

        with engine.begin() as connection:

            connection.execute(
                query,
                {"symbol": symbol},
            )

    # ==========================================================
    # Row Count
    # ==========================================================

    def row_count(self) -> int:

        query = text(
            """
            SELECT COUNT(*)
            FROM sentinel.market_regimes
            """
        )

        with engine.connect() as connection:

            return connection.execute(query).scalar()


# ==========================================================
# Test
# ==========================================================

if __name__ == "__main__":

    repo = RegimeRepository()

    print("=" * 50)
    print("REGIME REPOSITORY")
    print("=" * 50)

    print(repo.row_count())