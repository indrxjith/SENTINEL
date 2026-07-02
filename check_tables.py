from src.repository.market_repository import MarketRepository
from src.repository.var_repository import VarRepository
from src.repository.risk_score_repository import RiskScoreRepository
from src.repository.regime_repository import RegimeRepository

print("=" * 60)
print("MARKET PRICES")
market = MarketRepository().fetch_symbol("SPY")
print(market.columns.tolist())
print(market.tail())

print("=" * 60)
print("VAR")
var = VarRepository().fetch_symbol("SPY")
print(var.columns.tolist())
print(var.tail())

print("=" * 60)
print("RISK SCORES")
risk = RiskScoreRepository().fetch_symbol("SPY")
print(risk.columns.tolist())
print(risk.tail())

print("=" * 60)
print("REGIMES")
regime = RegimeRepository().fetch_symbol("SPY")
print(regime.columns.tolist())
print(regime.tail())