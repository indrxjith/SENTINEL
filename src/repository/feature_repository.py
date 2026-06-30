"""
Repository for engineered market features.
"""

from __future__ import annotations

import pandas as pd
from sqlalchemy import text

from src.utils.database import engine


class FeatureRepository:
    """
    Repository for the market_features table.
    """

    TABLE_NAME = "market_features"
    SCHEMA = "sentinel"

    # ==========================================================
    # Insert
    # ==========================================================

    def insert(
        self,
        data: pd.DataFrame,
    ) -> int:
        """
        Insert engineered features into PostgreSQL.
        """

        df = data.copy()

        # Remove auto-generated columns
        df = df.drop(
            columns=["id", "created_at"],
            errors="ignore",
        )

        # Remove raw market columns
        df = df.drop(
            columns=[
                "open",
                "high",
                "low",
                "close",
                "adjusted_close",
                "volume",
            ],
            errors="ignore",
        )

        print("\n======================================")
        print("INSERTING FEATURES")
        print("======================================")

        print(f"Rows    : {len(df):,}")
        print(f"Columns : {len(df.columns)}")

        try:

            df.to_sql(
                self.TABLE_NAME,
                engine,
                schema=self.SCHEMA,
                if_exists="append",
                index=False,
                method="multi",
            )

            print(f"\n✓ Successfully inserted {len(df):,} rows.")

            return len(df)

        except Exception as e:

            print("\n======================================")
            print("DATABASE INSERT FAILED")
            print("======================================")

            raise

    # ==========================================================
    # Fetch One Symbol
    # ==========================================================

    def fetch_symbol(
        self,
        symbol: str,
    ) -> pd.DataFrame:

        query = text(
            """
            SELECT *
            FROM sentinel.market_features
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
    # Fetch All
    # ==========================================================

    def fetch_all(
        self,
    ) -> pd.DataFrame:

        query = text(
            """
            SELECT *
            FROM sentinel.market_features
            ORDER BY symbol, trade_date
            """
        )

        return pd.read_sql(
            query,
            engine,
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
            FROM sentinel.market_features
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
            FROM sentinel.market_features
            """
        )

        with engine.connect() as connection:

            return connection.execute(query).scalar()


# ==========================================================
# Test
# ==========================================================

if __name__ == "__main__":

    repository = FeatureRepository()

    print("=" * 50)
    print("FEATURE REPOSITORY TEST")
    print("=" * 50)

    print(f"Rows in market_features: {repository.row_count():,}")