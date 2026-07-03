from data_loader import get_validation_summary
import datetime as dt

summary = get_validation_summary(
    "SPY",
    "historical",
    dt.date(2024, 12, 31),
)

print(summary)
print(type(summary))

if isinstance(summary, dict):
    for key, value in summary.items():
        print(f"\n{key}:")
        print(value)