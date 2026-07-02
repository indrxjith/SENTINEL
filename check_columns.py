from sqlalchemy import text
from src.utils.database import engine

tables = [
    "asset_beta",
    "asset_expected_shortfall",
    "asset_correlations",
    "market_features",
]

with engine.connect() as conn:

    for table in tables:

        print("=" * 60)
        print(table.upper())

        row = conn.execute(
            text(f"SELECT * FROM sentinel.{table} LIMIT 1")
        ).mappings().first()

        if row is None:
            print("Table is empty.")
        else:
            print(list(row.keys()))