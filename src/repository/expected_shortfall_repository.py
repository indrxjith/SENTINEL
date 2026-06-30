"""
Repository for Expected Shortfall (CVaR).
"""

from __future__ import annotations

import pandas as pd
from sqlalchemy import text

from src.utils.database import engine


class ExpectedShortfallRepository:

    TABLE_NAME = "asset_expected_shortfall"
    SCHEMA = "sentinel"

    # ==========================================================
    # Insert
    # ==========================================================

    def insert(self, data: pd.DataFrame) -> int:

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

    def delete_symbol(self, symbol: str):

        query = text("""
            DELETE
            FROM sentinel.asset_expected_shortfall
            WHERE symbol=:symbol
        """)

        with engine.begin() as connection:

            connection.execute(
                query,
                {"symbol": symbol},
            )

    # ==========================================================
    # Fetch Symbol
    # ==========================================================

    def fetch_symbol(self, symbol: str) -> pd.DataFrame:

        query = text("""
            SELECT *
            FROM sentinel.asset_expected_shortfall
            WHERE symbol=:symbol
            ORDER BY trade_date
        """)

        return pd.read_sql(
            query,
            engine,
            params={"symbol": symbol},
        )

    # ==========================================================
    # Row Count
    # ==========================================================

    def row_count(self):

        query = text("""
            SELECT COUNT(*)
            FROM sentinel.asset_expected_shortfall
        """)

        with engine.connect() as connection:

            return connection.execute(query).scalar()


if __name__ == "__main__":

    repository = ExpectedShortfallRepository()

    print("=" * 50)
    print("EXPECTED SHORTFALL REPOSITORY TEST")
    print("=" * 50)

    print(repository.row_count())