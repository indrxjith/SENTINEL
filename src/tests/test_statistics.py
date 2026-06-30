from src.analytics.statistics import RollingStatistics
from src.repository.feature_repository import FeatureRepository

repository = FeatureRepository()

df = repository.fetch_symbol("SPY")

returns = df["simple_return"]

print("=" * 60)
print("ROLLING STATISTICS TEST")
print("=" * 60)

print("\nRolling Mean (20)\n")
print(RollingStatistics.rolling_mean(returns, 20).tail())

print("\nRolling Std (20)\n")
print(RollingStatistics.rolling_std(returns, 20).tail())

print("\nRolling Z-Score (20)\n")
print(RollingStatistics.rolling_zscore(returns, 20).tail())