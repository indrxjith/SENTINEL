"""
Data validation module for the SENTINEL project.

Validates normalized market data before it is written
to PostgreSQL.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


# ==========================================================
# Validation Report
# ==========================================================

@dataclass
class ValidationReport:
    """Stores validation results."""

    is_valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add_error(self, message: str) -> None:
        self.is_valid = False
        self.errors.append(message)

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)

    def summary(self) -> str:
        """Return formatted validation report."""

        lines = [
            "=" * 60,
            "SENTINEL DATA VALIDATION REPORT",
            "=" * 60,
        ]

        if self.errors:
            lines.append("\nERRORS:")
            for error in self.errors:
                lines.append(f"  ✗ {error}")

        if self.warnings:
            lines.append("\nWARNINGS:")
            for warning in self.warnings:
                lines.append(f"  ⚠ {warning}")

        lines.append("\nSTATUS:")

        if self.is_valid:
            lines.append("  ✅ PASSED")
        else:
            lines.append("  ❌ FAILED")

        return "\n".join(lines)


# ==========================================================
# Data Validator
# ==========================================================

class DataValidator:
    """Validates normalized market data."""

    REQUIRED_COLUMNS = [
        "trade_date",
        "symbol",
        "open",
        "high",
        "low",
        "close",
        "adjusted_close",
        "volume",
    ]

    PRICE_COLUMNS = [
        "open",
        "high",
        "low",
        "close",
        "adjusted_close",
    ]

    def validate(self, data: pd.DataFrame) -> ValidationReport:
        """Run all validation checks."""

        report = ValidationReport()

        self._check_empty(data, report)
        self._check_columns(data, report)

        if not report.is_valid:
            return report

        self._check_dtypes(data, report)
        self._check_missing(data, report)
        self._check_duplicates(data, report)
        self._check_prices(data, report)
        self._check_volume(data, report)
        self._check_ohlc(data, report)
        self._check_dates(data, report)

        return report

    # -----------------------------------------------------

    def _check_empty(
        self,
        data: pd.DataFrame,
        report: ValidationReport,
    ) -> None:

        if data.empty:
            report.add_error("DataFrame is empty.")

    # -----------------------------------------------------

    def _check_columns(
        self,
        data: pd.DataFrame,
        report: ValidationReport,
    ) -> None:

        missing = [
            column
            for column in self.REQUIRED_COLUMNS
            if column not in data.columns
        ]

        if missing:
            report.add_error(f"Missing columns: {missing}")

    # -----------------------------------------------------

    def _check_dtypes(
        self,
        data: pd.DataFrame,
        report: ValidationReport,
    ) -> None:

        if not pd.api.types.is_datetime64_any_dtype(data["trade_date"]):
            report.add_error("trade_date must be datetime.")

        if not pd.api.types.is_string_dtype(data["symbol"]):
            report.add_error("symbol column must contain strings.")

        for column in self.PRICE_COLUMNS:

            if not pd.api.types.is_numeric_dtype(data[column]):
                report.add_error(f"{column} must be numeric.")

        if not pd.api.types.is_integer_dtype(data["volume"]):
            report.add_warning(
                "volume column is not stored as an integer."
            )

    # -----------------------------------------------------

    def _check_missing(
        self,
        data: pd.DataFrame,
        report: ValidationReport,
    ) -> None:

        missing = data.isna().sum()
        missing = missing[missing > 0]

        for column, count in missing.items():
            report.add_error(f"{column}: {count} missing values.")

    # -----------------------------------------------------

    def _check_duplicates(
        self,
        data: pd.DataFrame,
        report: ValidationReport,
    ) -> None:

        duplicate_rows = data.duplicated().sum()

        if duplicate_rows:
            report.add_error(
                f"{duplicate_rows} duplicate rows."
            )

        duplicate_dates = data.duplicated(
            subset=["symbol", "trade_date"]
        ).sum()

        if duplicate_dates:
            report.add_error(
                f"{duplicate_dates} duplicate (symbol, trade_date) rows."
            )

    # -----------------------------------------------------

    def _check_prices(
        self,
        data: pd.DataFrame,
        report: ValidationReport,
    ) -> None:

        for column in self.PRICE_COLUMNS:

            invalid = (data[column] <= 0).sum()

            if invalid:
                report.add_error(
                    f"{column}: {invalid} non-positive values."
                )

    # -----------------------------------------------------

    def _check_volume(
        self,
        data: pd.DataFrame,
        report: ValidationReport,
    ) -> None:

        invalid = (data["volume"] < 0).sum()

        if invalid:
            report.add_error(
                f"{invalid} negative volume values."
            )

    # -----------------------------------------------------

    def _check_ohlc(
        self,
        data: pd.DataFrame,
        report: ValidationReport,
    ) -> None:
        """
        Validate OHLC relationships.
        """

        invalid_rows = data[
            (data["high"] < data["low"])
            | (data["high"] < data["open"])
            | (data["high"] < data["close"])
            | (data["low"] > data["open"])
            | (data["low"] > data["close"])
        ]

        if not invalid_rows.empty:

            report.add_error(
                f"{len(invalid_rows)} rows violate OHLC rules."
            )

            print("\n" + "=" * 60)
            print("INVALID OHLC ROWS")
            print("=" * 60)

            print(
                invalid_rows[
                    [
                        "trade_date",
                        "symbol",
                        "open",
                        "high",
                        "low",
                        "close",
                        "adjusted_close",
                        "volume",
                    ]
                ].to_string(index=False)
            )

            print("=" * 60)

    # -----------------------------------------------------

    def _check_dates(
        self,
        data: pd.DataFrame,
        report: ValidationReport,
    ) -> None:

        if not data["trade_date"].is_monotonic_increasing:
            report.add_warning(
                "trade_date is not sorted."
            )


# ==========================================================
# Test
# ==========================================================

if __name__ == "__main__":

    from src.ingestion.market_downloader import MarketDownloader

    print("\nDownloading SPY...\n")

    downloader = MarketDownloader()
    validator = DataValidator()

    try:

        df = downloader.download("SPY")

        print("Data Types:")
        print(df.dtypes)
        print()

        report = validator.validate(df)

        print(report.summary())

    except Exception as e:

        print("\n❌ Unable to download SPY.\n")
        print(e)