"""
Repository for asset correlations.
"""

from __future__ import annotations

import pandas as pd
from sqlalchemy import text

from src.utils.database import engine


class CorrelationRepository:
    """
    Repository for asset_correlations table.
    """

    TABLE_NAME = "asset_correlations"
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
    # Fetch All
    # ==========================================================

    def fetch_all(self) -> pd.DataFrame:

        query = text(
            """
            SELECT *
            FROM sentinel.asset_correlations
            ORDER BY trade_date
            """
        )

        return pd.read_sql(query, engine)

    # ==========================================================
    # Delete All
    # ==========================================================

    def delete_all(self):

        query = text(
            """
            DELETE
            FROM sentinel.asset_correlations
            """
        )

        with engine.begin() as connection:

            connection.execute(query)

    # ==========================================================
    # Row Count
    # ==========================================================

    def row_count(self) -> int:

        query = text(
            """
            SELECT COUNT(*)
            FROM sentinel.asset_correlations
            """
        )

        with engine.connect() as connection:

            return connection.execute(query).scalar()


if __name__ == "__main__":

    repository = CorrelationRepository()

    print("=" * 50)
    print("CORRELATION REPOSITORY TEST")
    print("=" * 50)

    print(f"Rows: {repository.row_count():,}")