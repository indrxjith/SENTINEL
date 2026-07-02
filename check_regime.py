import pandas as pd
from sqlalchemy import text

from src.utils.database import engine

df = pd.read_sql(
    text("SELECT * FROM sentinel.market_regimes LIMIT 5"),
    engine,
)

print("=" * 50)
print(df.columns.tolist())
print("=" * 50)
print(df)