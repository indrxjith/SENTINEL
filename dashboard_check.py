import datetime as dt

from data_loader import get_market_regime

df = get_market_regime(
    "SPY",
    dt.date(2024, 1, 1),
    dt.date(2024, 12, 31),
)

print("=" * 60)
print(df.head())
print("=" * 60)
print(df.columns.tolist())
print("=" * 60)

if "regime" in df.columns:
    print(df["regime"].value_counts(dropna=False))
else:
    print("No 'regime' column found!")