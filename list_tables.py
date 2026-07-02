from sqlalchemy import text
from src.utils.database import engine

with engine.connect() as conn:

    tables = conn.execute(text("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema='sentinel'
        ORDER BY table_name;
    """)).fetchall()

    print("\nTABLE NAME".ljust(35), "ROWS")
    print("-" * 45)

    for (table,) in tables:

        rows = conn.execute(
            text(f"SELECT COUNT(*) FROM sentinel.{table}")
        ).scalar()

        print(f"{table:<35} {rows:,}")