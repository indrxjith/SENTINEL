"""
Repository for rolling beta values.
"""

from __future__ import annotations

import pandas as pd
from sqlalchemy import text

from src.utils.database import engine


class BetaRepository:
    """
    Repository for asset_beta table.
    """

    TABLE_NAME = "asset_beta"
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
    # Delete Symbol
    # ==========================================================

    def delete_symbol(
        self,
        symbol: str,
        benchmark: str,
    ):

        query = text(
            """
            DELETE
            FROM sentinel.asset_beta
            WHERE symbol=:symbol
            AND benchmark=:benchmark
            """
        )

        with engine.begin() as connection:

            connection.execute(
                query,
                {
                    "symbol": symbol,
                    "benchmark": benchmark,
                },
            )

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
            FROM sentinel.asset_beta
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
    # Row Count
    # ==========================================================

    def row_count(self) -> int:

        query = text(
            """
            SELECT COUNT(*)
            FROM sentinel.asset_beta
            """
        )

        with engine.connect() as connection:

            return connection.execute(query).scalar()


if __name__ == "__main__":

    repository = BetaRepository()

    print("=" * 50)
    print("BETA REPOSITORY TEST")
    print("=" * 50)

    print(f"Rows: {repository.row_count():,}")