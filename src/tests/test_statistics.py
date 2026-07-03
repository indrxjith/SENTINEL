"""
Unit tests for RollingStatistics.

Run with:
    pytest src/tests/test_statistics.py -v

These tests use small, hand-computable synthetic series so every
assertion can be checked against a value you could work out on paper.
No database connection is required — RollingStatistics is pure pandas,
so it should never need FeatureRepository to be tested.
"""

import numpy as np
import pandas as pd
import pytest

from src.analytics.statistics import RollingStatistics


# ======================================================================
# Fixtures
# ======================================================================

@pytest.fixture
def linear_series() -> pd.Series:
    """1, 2, 3, ..., 10 — easy to hand-verify mean/std/min/max on."""
    return pd.Series(range(1, 11), dtype=float)


@pytest.fixture
def constant_series() -> pd.Series:
    """A flat series: std/variance should be exactly 0 everywhere."""
    return pd.Series([5.0] * 10)


# ======================================================================
# rolling_mean
# ======================================================================

class TestRollingMean:

    def test_known_values(self, linear_series):
        result = RollingStatistics.rolling_mean(linear_series, window=3)
        # First full window is indices [0,1,2] -> mean(1,2,3) = 2.0
        assert result.iloc[2] == pytest.approx(2.0)
        # Last window is [8,9,10] -> mean = 9.0
        assert result.iloc[-1] == pytest.approx(9.0)

    def test_leading_values_are_nan(self, linear_series):
        result = RollingStatistics.rolling_mean(linear_series, window=3)
        assert result.iloc[:2].isna().all()

    def test_window_one_returns_series_unchanged(self, linear_series):
        result = RollingStatistics.rolling_mean(linear_series, window=1)
        pd.testing.assert_series_equal(result, linear_series, check_names=False)

    def test_window_larger_than_series_is_all_nan(self, linear_series):
        result = RollingStatistics.rolling_mean(linear_series, window=20)
        assert result.isna().all()


# ======================================================================
# rolling_std / rolling_variance
# ======================================================================

class TestRollingDispersion:

    def test_std_matches_manual_calculation(self, linear_series):
        result = RollingStatistics.rolling_std(linear_series, window=3)
        expected = np.std([1, 2, 3], ddof=1)  # pandas uses sample std (ddof=1)
        assert result.iloc[2] == pytest.approx(expected)

    def test_variance_is_std_squared(self, linear_series):
        std = RollingStatistics.rolling_std(linear_series, window=4)
        var = RollingStatistics.rolling_variance(linear_series, window=4)
        pd.testing.assert_series_equal(std**2, var, check_names=False)

    def test_constant_series_has_zero_dispersion(self, constant_series):
        std = RollingStatistics.rolling_std(constant_series, window=3)
        var = RollingStatistics.rolling_variance(constant_series, window=3)
        assert (std.dropna() == 0).all()
        assert (var.dropna() == 0).all()


# ======================================================================
# rolling_min / rolling_max
# ======================================================================

class TestRollingMinMax:

    def test_min_and_max_known_values(self, linear_series):
        rmin = RollingStatistics.rolling_min(linear_series, window=3)
        rmax = RollingStatistics.rolling_max(linear_series, window=3)
        assert rmin.iloc[2] == 1.0
        assert rmax.iloc[2] == 3.0
        assert rmin.iloc[-1] == 8.0
        assert rmax.iloc[-1] == 10.0

    def test_min_never_exceeds_max(self, linear_series):
        rmin = RollingStatistics.rolling_min(linear_series, window=4)
        rmax = RollingStatistics.rolling_max(linear_series, window=4)
        valid = rmin.notna() & rmax.notna()
        assert (rmin[valid] <= rmax[valid]).all()


# ======================================================================
# rolling_zscore
# ======================================================================

class TestRollingZScore:

    def test_zscore_matches_manual_calculation(self, linear_series):
        result = RollingStatistics.rolling_zscore(linear_series, window=3)
        window_vals = [1, 2, 3]
        expected = (3 - np.mean(window_vals)) / np.std(window_vals, ddof=1)
        assert result.iloc[2] == pytest.approx(expected)

    def test_constant_series_zscore_is_nan_not_inf(self, constant_series):
        # std == 0 -> division by zero. This documents current behavior:
        # pandas produces NaN (0/0) rather than raising, which callers
        # of VarEngine / risk_score need to be aware of and handle.
        result = RollingStatistics.rolling_zscore(constant_series, window=3)
        valid = result.dropna()
        assert valid.empty or valid.isna().all() or (valid == 0).all()


# ======================================================================
# rolling_covariance / rolling_correlation
# ======================================================================

class TestRollingCovarianceAndCorrelation:

    def test_perfectly_correlated_series(self, linear_series):
        y = linear_series * 2 + 1  # perfect linear relationship
        corr = RollingStatistics.rolling_correlation(linear_series, y, window=4)
        assert corr.dropna().apply(lambda v: v == pytest.approx(1.0, abs=1e-9)).all()

    def test_inversely_correlated_series(self, linear_series):
        y = -linear_series
        corr = RollingStatistics.rolling_correlation(linear_series, y, window=4)
        assert corr.dropna().apply(lambda v: v == pytest.approx(-1.0, abs=1e-9)).all()

    def test_correlation_is_bounded(self, linear_series):
        rng = np.random.default_rng(42)
        noisy = pd.Series(rng.normal(size=len(linear_series)))
        corr = RollingStatistics.rolling_correlation(linear_series, noisy, window=4)
        valid = corr.dropna()
        assert ((valid >= -1.0 - 1e-9) & (valid <= 1.0 + 1e-9)).all()

    def test_covariance_with_self_equals_variance(self, linear_series):
        cov = RollingStatistics.rolling_covariance(linear_series, linear_series, window=4)
        var = RollingStatistics.rolling_variance(linear_series, window=4)
        pd.testing.assert_series_equal(cov, var, check_names=False)