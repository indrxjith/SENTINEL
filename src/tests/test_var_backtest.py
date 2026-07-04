"""
Unit tests for VarBacktestEngine.

Run with:
    pytest src/tests/test_var_backtest.py -v

VarBacktestEngine.__init__ constructs a real VarRepository and
FeatureRepository, but those classes don't touch the database until a
query method (fetch_symbol, insert, ...) is actually called -- the
SQLAlchemy engine they wrap is lazy. So these tests build the engine
normally and then monkeypatch fetch_symbol on each repository
instance to return hand-built DataFrames, instead of mocking at the
module/class level. No live Postgres connection is ever made.

Small, hand-verifiable fixtures are used throughout (10 rows, constant
VaR thresholds) so every breach flag and rolling value can be checked
against a value worked out by hand. WINDOW and BASEL_WINDOW are
overridden to small numbers on the engine instance where needed --
they are plain instance/class attributes, not hardcoded constants, so
this doesn't require 252/250 rows of fixture data to exercise the
rolling logic.
"""

import numpy as np
import pandas as pd
import pytest

from src.analytics.model_validation import ModelValidation
from src.analytics.var_backtest import VarBacktestEngine


# ======================================================================
# Fixtures
# ======================================================================

@pytest.fixture
def engine() -> VarBacktestEngine:
    """
    A real VarBacktestEngine. Repository DB calls are stubbed per-test
    via monkeypatching fetch_symbol, not here, since different tests
    need different fixture data.
    """
    return VarBacktestEngine()


@pytest.fixture
def ten_day_var_returns():
    """
    10 trading days, constant VaR thresholds, hand-picked returns so
    breaches can be verified on paper.

    historical_var_95 = -0.03 -> breach_95 when return < -0.03
    historical_var_99 = -0.06 -> breach_99 when return < -0.06

    returns:      -.05  .01  -.02  .03  -.10  .02  -.01  .04  -.03  .00
    breach_95:      T    F    F    F     T    F     F    F    F     F   (2 total)
    breach_99:      F    F    F    F     T    F     F    F    F     F   (1 total)
    """
    dates = pd.date_range("2020-01-01", periods=10, freq="D")
    var_df = pd.DataFrame({
        "trade_date": dates,
        "symbol": "TEST",
        "historical_var_95": -0.03,
        "historical_var_99": -0.06,
    })
    returns_df = pd.DataFrame({
        "trade_date": dates,
        "symbol": "TEST",
        "simple_return": [-0.05, 0.01, -0.02, 0.03, -0.10,
                           0.02, -0.01, 0.04, -0.03, 0.00],
    })
    return var_df, returns_df


def stub_repositories(engine, var_df, returns_df):
    """Point both repositories' fetch_symbol at fixed DataFrames."""
    engine.var_repository.fetch_symbol = lambda symbol: var_df
    engine.feature_repository.fetch_symbol = lambda symbol: returns_df


# ======================================================================
# calculate()
# ======================================================================

class TestCalculate:

    def test_breach_flags_match_hand_computed_values(
        self, engine, ten_day_var_returns
    ):
        var_df, returns_df = ten_day_var_returns
        stub_repositories(engine, var_df, returns_df)

        df = engine.calculate("TEST")

        assert df["breach_95"].tolist() == [
            True, False, False, False, True,
            False, False, False, False, False,
        ]
        assert df["breach_99"].tolist() == [
            False, False, False, False, True,
            False, False, False, False, False,
        ]
        assert df["breach_95"].sum() == 2
        assert df["breach_99"].sum() == 1

    def test_boundary_return_equal_to_var_is_not_a_breach(self, engine):
        # A breach is strictly "return < VaR", not "<=" -- a return
        # exactly at the threshold should NOT count as a breach. Each
        # threshold is tested against a return that ONLY sits at that
        # threshold (comfortably above the other), so a false failure
        # from the other, unrelated column can't leak into either check.
        dates = pd.date_range("2020-01-01", periods=3, freq="D")
        var_df = pd.DataFrame({
            "trade_date": dates, "symbol": "TEST",
            "historical_var_95": -0.03, "historical_var_99": -0.06,
        })
        returns_df = pd.DataFrame({
            "trade_date": dates, "symbol": "TEST",
            # row0: exactly at the 95% threshold, well above the 99% one
            # row1: exactly at the 99% threshold
            # row2: comfortably positive, nowhere near either threshold
            "simple_return": [-0.03, -0.06, 0.0],
        })
        stub_repositories(engine, var_df, returns_df)

        df = engine.calculate("TEST")
        # Row 0 sits exactly on the 95% line -> not a breach there.
        assert df["breach_95"].iloc[0] == False
        # Row 1 sits exactly on the 99% line -> not a breach there
        # (it IS a legitimate 95% breach, since -0.06 < -0.03).
        assert df["breach_99"].iloc[1] == False
        assert df["breach_95"].iloc[1] == True
        # Row 2 breaches neither.
        assert df["breach_95"].iloc[2] == False
        assert df["breach_99"].iloc[2] == False

    def test_rows_are_sorted_chronologically_even_if_inputs_are_shuffled(
        self, engine, ten_day_var_returns
    ):
        var_df, returns_df = ten_day_var_returns
        shuffled_var = var_df.sample(frac=1, random_state=1).reset_index(drop=True)
        shuffled_returns = returns_df.sample(frac=1, random_state=2).reset_index(drop=True)
        stub_repositories(engine, shuffled_var, shuffled_returns)

        df = engine.calculate("TEST")

        assert df["trade_date"].is_monotonic_increasing
        # And breaches still line up with the correct dates despite
        # the shuffled input order (not just "some" order).
        assert df["breach_95"].tolist() == [
            True, False, False, False, True,
            False, False, False, False, False,
        ]

    def test_inner_join_drops_unmatched_dates_on_either_side(self, engine):
        # A date present in var_df but missing from returns_df (or
        # vice versa) should be dropped by the merge, not filled with
        # NaN -- confirms this is an inner join, not an outer one.
        dates = pd.date_range("2020-01-01", periods=10, freq="D")
        var_df = pd.DataFrame({
            "trade_date": dates, "symbol": "TEST",
            "historical_var_95": -0.03, "historical_var_99": -0.06,
        })
        returns_df = pd.DataFrame({
            "trade_date": dates, "symbol": "TEST",
            "simple_return": [0.0] * 10,
        })
        returns_missing = returns_df.drop(index=3).reset_index(drop=True)
        stub_repositories(engine, var_df, returns_missing)

        df = engine.calculate("TEST")

        assert len(df) == 9
        assert dates[3] not in df["trade_date"].values

    def test_rolling_breach_rate_matches_manual_mean(
        self, engine, ten_day_var_returns
    ):
        var_df, returns_df = ten_day_var_returns
        stub_repositories(engine, var_df, returns_df)
        engine.WINDOW = 3  # small window so the fixture can cover it

        df = engine.calculate("TEST")

        # First 2 rows have no full 3-row window yet.
        assert df["rolling_breach_rate_95"].iloc[:2].isna().all()
        # Window covering rows 0-2 (breaches: T,F,F) -> 1/3 * 100.
        assert df["rolling_breach_rate_95"].iloc[2] == pytest.approx(100 / 3)
        # Window covering rows 2-4 (breaches: F,F,T) -> 1/3 * 100.
        assert df["rolling_breach_rate_95"].iloc[4] == pytest.approx(100 / 3)

    def test_only_expected_columns_are_kept_from_returns(
        self, engine, ten_day_var_returns
    ):
        var_df, returns_df = ten_day_var_returns
        # Add a column that calculate() should not need or leak.
        returns_df = returns_df.assign(unrelated_column="noise")
        stub_repositories(engine, var_df, returns_df)

        df = engine.calculate("TEST")
        assert "unrelated_column" not in df.columns


# ======================================================================
# rolling_basel_zones()
# ======================================================================

class TestRollingBaselZones:

    def test_zone_matches_model_validation_directly(self, engine):
        # Cross-check against ModelValidation.basel_traffic_light
        # itself, rather than hardcoding an expected zone string, so
        # this test stays correct if the Basel boundaries ever change.
        engine.BASEL_WINDOW = 5
        dates = pd.date_range("2020-01-01", periods=8, freq="D")
        breach = [0, 0, 0, 0, 1, 0, 0, 0]
        df = pd.DataFrame({"trade_date": dates, "breach_test": breach})

        result = engine.rolling_basel_zones(df, "breach_test")

        expected_zone = ModelValidation.basel_traffic_light(1, 5)["zone"]
        # Rows 4-7 have a full 5-row window containing the single
        # exception (indices 0-4, 1-5, 2-6, 3-7 all include index 4).
        assert (result["basel_zone"].iloc[4:8] == expected_zone).all()

    def test_leading_rows_without_a_full_window_are_nan(self, engine):
        engine.BASEL_WINDOW = 5
        dates = pd.date_range("2020-01-01", periods=8, freq="D")
        df = pd.DataFrame({"trade_date": dates, "breach_test": [0] * 8})

        result = engine.rolling_basel_zones(df, "breach_test")

        assert result["rolling_250d_exceptions"].iloc[:4].isna().all()
        assert result["basel_zone"].iloc[:4].isna().all()

    def test_returns_all_nan_when_shorter_than_window(self, engine, capsys):
        engine.BASEL_WINDOW = 10
        dates = pd.date_range("2020-01-01", periods=5, freq="D")
        df = pd.DataFrame({"trade_date": dates, "breach_test": [0, 0, 1, 0, 0]})

        result = engine.rolling_basel_zones(df, "breach_test")

        assert result["rolling_250d_exceptions"].isna().all()
        assert "Not enough observations" in capsys.readouterr().out

    def test_exception_counts_match_manual_rolling_sum(self, engine):
        engine.BASEL_WINDOW = 4
        dates = pd.date_range("2020-01-01", periods=10, freq="D")
        breach = [1, 0, 1, 0, 0, 1, 1, 1, 0, 0]
        df = pd.DataFrame({"trade_date": dates, "breach_test": breach})

        result = engine.rolling_basel_zones(df, "breach_test")

        expected = pd.Series(breach).rolling(4).sum()
        pd.testing.assert_series_equal(
            result["rolling_250d_exceptions"], expected,
            check_names=False,
        )


# ======================================================================
# summary() -- smoke tests
# ======================================================================
# summary() is a print-based report rather than a function with a
# return value, so these tests focus on (a) it runs without raising
# for realistic and edge-case inputs, and (b) the printed report
# contains the pass/fail verdicts a reader would rely on.

class TestSummarySmoke:

    def _make_df(self, n=30, seed=0, var95=-0.02, var99=-0.04):
        dates = pd.date_range("2020-01-01", periods=n, freq="D")
        rng = np.random.default_rng(seed)
        returns = rng.normal(0, 0.01, n)
        df = pd.DataFrame({
            "trade_date": dates,
            "historical_var_95": var95,
            "historical_var_99": var99,
        })
        df["simple_return"] = returns
        df["breach_95"] = df["simple_return"] < df["historical_var_95"]
        df["breach_99"] = df["simple_return"] < df["historical_var_99"]
        return df

    def test_runs_without_error_and_reports_both_confidence_levels(
        self, engine, capsys
    ):
        df = self._make_df()
        engine.BASEL_WINDOW = 10

        engine.summary(df)  # must not raise

        out = capsys.readouterr().out
        assert "95% HISTORICAL VaR" in out
        assert "99% HISTORICAL VaR" in out
        assert "Kupiec Test" in out

    def test_basel_analysis_only_runs_at_99_percent(self, engine, capsys):
        df = self._make_df()
        engine.BASEL_WINDOW = 10

        engine.summary(df)

        out = capsys.readouterr().out
        # 95% section explicitly states Basel doesn't apply there.
        assert "Not Applicable" in out
        assert "defined for 99% one-day VaR" in out

    def test_handles_zero_exception_edge_case_without_raising(
        self, engine, capsys
    ):
        # No breaches at all -> Christoffersen is degenerate for both
        # confidence levels. summary() must handle the None fields
        # gracefully (print "N/A") rather than crashing on formatting
        # a None with an f-string format spec.
        n = 20
        dates = pd.date_range("2020-01-01", periods=n, freq="D")
        df = pd.DataFrame({
            "trade_date": dates,
            "historical_var_95": -0.10,
            "historical_var_99": -0.20,
            "simple_return": [0.001] * n,
        })
        df["breach_95"] = df["simple_return"] < df["historical_var_95"]
        df["breach_99"] = df["simple_return"] < df["historical_var_99"]

        engine.summary(df)  # must not raise

        out = capsys.readouterr().out
        assert "Christoffersen Test    : N/A" in out
        assert "Conditional Coverage   : N/A" in out