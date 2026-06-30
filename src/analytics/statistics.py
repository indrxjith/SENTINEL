"""
Rolling statistical functions for SENTINEL.
"""

from __future__ import annotations

import pandas as pd


class RollingStatistics:
    """
    Shared statistical functions used by all analytics modules.
    """

    # ==========================================================
    # Rolling Mean
    # ==========================================================

    @staticmethod
    def rolling_mean(
        series: pd.Series,
        window: int,
    ) -> pd.Series:

        return series.rolling(window).mean()

    # ==========================================================
    # Rolling Standard Deviation
    # ==========================================================

    @staticmethod
    def rolling_std(
        series: pd.Series,
        window: int,
    ) -> pd.Series:

        return series.rolling(window).std()

    # ==========================================================
    # Rolling Minimum
    # ==========================================================

    @staticmethod
    def rolling_min(
        series: pd.Series,
        window: int,
    ) -> pd.Series:

        return series.rolling(window).min()

    # ==========================================================
    # Rolling Maximum
    # ==========================================================

    @staticmethod
    def rolling_max(
        series: pd.Series,
        window: int,
    ) -> pd.Series:

        return series.rolling(window).max()

    # ==========================================================
    # Rolling Variance
    # ==========================================================

    @staticmethod
    def rolling_variance(
        series: pd.Series,
        window: int,
    ) -> pd.Series:

        return series.rolling(window).var()

    # ==========================================================
    # Rolling Z-Score
    # ==========================================================

    @staticmethod
    def rolling_zscore(
        series: pd.Series,
        window: int,
    ) -> pd.Series:

        mean = series.rolling(window).mean()

        std = series.rolling(window).std()

        return (series - mean) / std

    # ==========================================================
    # Rolling Covariance
    # ==========================================================

    @staticmethod
    def rolling_covariance(
        x: pd.Series,
        y: pd.Series,
        window: int,
    ) -> pd.Series:

        return x.rolling(window).cov(y)

    # ==========================================================
    # Rolling Correlation
    # ==========================================================

    @staticmethod
    def rolling_correlation(
        x: pd.Series,
        y: pd.Series,
        window: int,
    ) -> pd.Series:

        return x.rolling(window).corr(y)