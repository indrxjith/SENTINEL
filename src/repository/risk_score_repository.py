"""
Repository for Risk Scores.
"""

from __future__ import annotations

import pandas as pd
from sqlalchemy import text

from src.utils.database import engine


class RiskScoreRepository:
    """
    Repository for risk_scores table.
    """

    TABLE_NAME = "risk_scores"
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
            FROM sentinel.risk_scores
            WHERE symbol = :symbol
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

    def fetch_all(self) -> pd.DataFrame:

        query = text(
            """
            SELECT *
            FROM sentinel.risk_scores
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
            FROM sentinel.risk_scores
            WHERE symbol = :symbol
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
            FROM sentinel.risk_scores
            """
        )

        with engine.connect() as connection:

            return connection.execute(query).scalar()


# ==========================================================
# Test
# ==========================================================

if __name__ == "__main__":

    repository = RiskScoreRepository()

    print("=" * 50)
    print("RISK SCORE REPOSITORY")
    print("=" * 50)

    print(f"Rows: {repository.row_count():,}")