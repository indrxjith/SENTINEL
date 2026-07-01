"""
Value at Risk (VaR) Backtesting Engine for SENTINEL.

Compares predicted VaR against realized returns
to evaluate the accuracy of the VaR model.
"""

from __future__ import annotations

import pandas as pd

from src.repository.var_repository import VarRepository
from src.repository.feature_repository import FeatureRepository
from src.analytics.model_validation import ModelValidation  # FIX 1: was missing


class VarBacktestEngine:
    """
    Performs Historical VaR backtesting.

    A breach occurs when:

        Actual Return < Historical VaR

    Example

        Return = -4.2%
        VaR95  = -3.1%

        -> Breach = True
    """

    WINDOW = 252
    BASEL_WINDOW = 250  # standard Basel supervisory backtesting window

    def __init__(self):

        self.var_repository = VarRepository()
        self.feature_repository = FeatureRepository()

    # ==========================================================
    # Load Data
    # ==========================================================

    def load_var(
        self,
        symbol: str,
    ) -> pd.DataFrame:

        return self.var_repository.fetch_symbol(symbol)

    def load_returns(
        self,
        symbol: str,
    ) -> pd.DataFrame:

        return self.feature_repository.fetch_symbol(symbol)

    # ==========================================================
    # Backtest
    # ==========================================================

    def calculate(
        self,
        symbol: str,
    ) -> pd.DataFrame:

        var_df = self.load_var(symbol)
        returns_df = self.load_returns(symbol)

        # FIX 2: Do not trust repository/DB row order. A Postgres query
        # without an explicit ORDER BY makes no guarantee about the
        # order rows are returned in, and pd.merge() does not restore
        # chronological order either. Every time-series computation in
        # this class (breaches, rolling means) depends on df being in
        # strict trade_date order -- sort defensively at the source,
        # not just here, but ALSO here as a second line of defense.
        var_df = var_df.sort_values("trade_date").reset_index(drop=True)
        returns_df = returns_df.sort_values("trade_date").reset_index(drop=True)

        returns_df = returns_df[
            [
                "trade_date",
                "symbol",
                "simple_return",
            ]
        ]

        n_var_before = len(var_df)
        n_returns_before = len(returns_df)

        df = pd.merge(
            var_df,
            returns_df,
            on=[
                "trade_date",
                "symbol",
            ],
            how="inner",
        )

        # FIX 4: merge() can silently drop rows on either side (e.g. VaR
        # rows with no matching return, or vice versa). Report the gap
        # so a warm-up-period explanation (first WINDOW rows have no
        # VaR) can be distinguished from real data loss, instead of the
        # row count difference being invisible.
        # Diagnostics are still computed (cheap, and useful if row counts
        # ever look wrong) but no longer printed on every run -- this was
        # internal debugging output, not something a report reader needs
        # to see. Uncomment the print if debugging a merge issue again.
        n_merged = len(df)
        n_dropped_var = n_var_before - n_merged
        n_dropped_returns = n_returns_before - n_merged
        # print(
        #     f"  merge diagnostics: var_rows={n_var_before}, "
        #     f"return_rows={n_returns_before}, merged_rows={n_merged}, "
        #     f"var_rows_unmatched≈{n_dropped_var}, "
        #     f"return_rows_unmatched≈{n_dropped_returns}"
        # )

        # Re-sort after merge as well -- pd.merge with how="inner" on
        # two already-sorted frames should preserve order, but this is
        # not documented as a guarantee across pandas versions, so it
        # is enforced explicitly rather than assumed.
        df = df.sort_values("trade_date").reset_index(drop=True)

        # ------------------------------------------------------
        # Historical VaR Breaches
        # ------------------------------------------------------

        df["breach_95"] = (
            df["simple_return"]
            < df["historical_var_95"]
        )

        df["breach_99"] = (
            df["simple_return"]
            < df["historical_var_99"]
        )

        # ------------------------------------------------------
        # Rolling breach rate
        # ------------------------------------------------------
        # Only meaningful now that df is guaranteed chronologically
        # ordered above -- a rolling window over out-of-order rows
        # computes a rate over an arbitrary set of dates, not a
        # trailing window in time.

        df["rolling_breach_rate_95"] = (
            df["breach_95"]
            .rolling(self.WINDOW)
            .mean()
            * 100
        )

        df["rolling_breach_rate_99"] = (
            df["breach_99"]
            .rolling(self.WINDOW)
            .mean()
            * 100
        )

        return df

    # ==========================================================
    # Basel rolling-window backtesting
    # ==========================================================

    def rolling_basel_zones(
        self,
        df: pd.DataFrame,
        breach_col: str,
    ) -> pd.DataFrame:
        """
        Compute the Basel traffic-light zone for EVERY rolling 250-day
        window across the sample, instead of misapplying the test to
        the full multi-year aggregate (which produces a meaningless
        zone label -- see discussion: a model can be GREEN in every
        single rolling year and still show a large lifetime exception
        count, or the reverse).

        Returns the full time series of rolling exception counts and
        zones, and prints the single worst (maximum-exception) window
        found -- the number a real model validation report would
        actually flag to a risk committee.
        """
        exceptions_250 = df[breach_col].rolling(self.BASEL_WINDOW).sum()

        zones = exceptions_250.apply(
            lambda n: (
                ModelValidation.basel_traffic_light(
                    int(n), self.BASEL_WINDOW
                )["zone"]
                if pd.notna(n)
                else None
            )
        )

        result = pd.DataFrame({
            "trade_date": df["trade_date"],
            "rolling_250d_exceptions": exceptions_250,
            "basel_zone": zones,
        })

        valid_result = result.dropna(subset=["rolling_250d_exceptions"])

        if valid_result.empty:
            print("  Not enough observations yet for a full 250-day window.")
            return result

        worst_window = valid_result.loc[
            valid_result["rolling_250d_exceptions"].idxmax()
        ]

        print(
            f"  Worst 250-day window: "
            f"{int(worst_window['rolling_250d_exceptions'])} exceptions, "
            f"ending {worst_window['trade_date']}, "
            f"zone={worst_window['basel_zone'].upper()}"
        )

        zone_counts = valid_result["basel_zone"].value_counts()
        for zone in ("green", "yellow", "red"):
            n_windows = int(zone_counts.get(zone, 0))
            print(f"  Windows in {zone.upper():6s}: {n_windows}")

        return result

    # ==========================================================
    # Summary
    # ==========================================================

    def summary(
        self,
        df: pd.DataFrame,
    ):
        # FIX 3: this entire method body was previously indented at the
        # same level as `def summary`, which is an IndentationError in
        # Python -- nothing in this class could have run with that in
        # place. Re-indented one level under the method definition.

        print("\n" + "=" * 70)
        print("MODEL VALIDATION REPORT")
        print("=" * 70)

        validations = [
            ("95%", "historical_var_95", "breach_95", 0.95),
            ("99%", "historical_var_99", "breach_99", 0.99),
        ]

        for label, var_col, breach_col, confidence in validations:

            valid = df.dropna(subset=[var_col])

            hits = valid[breach_col].astype(int).tolist()

            kupiec = ModelValidation.kupiec_test(
                breaches=hits,
                confidence_level=confidence,
            )

            christoffersen = ModelValidation.christoffersen_test(
                breaches=hits,
            )

            conditional = ModelValidation.conditional_coverage_test(
                breaches=hits,
                confidence_level=confidence,
            )

            print("\n" + "-" * 70)
            print(f"{label} HISTORICAL VaR")
            print("-" * 70)

            print(
                f"Kupiec Test            : {'PASS ✅' if kupiec['passed'] else 'FAIL ❌'}"
            )

            if christoffersen["passed"] is None:
                print("Christoffersen Test    : N/A")
            else:
                print(
                    f"Christoffersen Test    : {'PASS ✅' if christoffersen['passed'] else 'FAIL ❌'}"
                )

            if conditional["passed"] is None:
                print("Conditional Coverage   : N/A")
            else:
                print(
                    f"Conditional Coverage   : {'PASS ✅' if conditional['passed'] else 'FAIL ❌'}"
                )

            # IMPROVEMENT 1: dropped the lifetime "Basel Zone" line.
            # Basel's traffic-light test is defined on a rolling 250-day
            # window, not a multi-year aggregate -- the real number is
            # the "Rolling Basel Analysis" section printed below, so
            # printing a second, non-standard "lifetime" zone here was
            # redundant at best and misleading at worst (e.g. it showed
            # GREEN for the 99% model in a run where Kupiec failed).

            print()

            print(
                f"Exceptions             : {kupiec['n_exceptions']} / {kupiec['n_observations']}"
            )

            print(
                f"Observed Rate          : {kupiec['observed_rate'] * 100:.2f}%"
            )

            print(
                f"Expected Rate          : {kupiec['expected_rate'] * 100:.2f}%"
            )

            print(
                f"Kupiec LR              : {kupiec['lr_statistic']:.4f}"
            )

            if christoffersen["lr_statistic"] is not None:
                print(
                    f"Christoffersen LR      : {christoffersen['lr_statistic']:.4f}"
                )

            if conditional["lr_statistic"] is not None:
                print(
                    f"Conditional Coverage LR: {conditional['lr_statistic']:.4f}"
                )

            print(
                f"Kupiec p-value         : {kupiec['p_value']:.4f}"
            )

            if christoffersen["p_value"] is not None:
                print(
                    f"Christoffersen p-value : {christoffersen['p_value']:.4f}"
                )

            if conditional["p_value"] is not None:
                print(
                    f"Conditional p-value    : {conditional['p_value']:.4f}"
                )

            # Diagnostic: surface the raw transition matrix so a
            # degenerate/suspicious pattern (e.g. a single 0->1
            # transition covering nearly all exceptions) is visible
            # directly in the report, not just discoverable by
            # digging into the returned dict manually.
            transition_ok = not christoffersen.get("degenerate", True)

            if transition_ok:
                tm = christoffersen["transition_matrix"]
                print(
                    f"Transition matrix      : n00={tm['n00']} "
                    f"n01={tm['n01']} n10={tm['n10']} n11={tm['n11']}"
                )

                # IMPROVEMENT 2: conditional breach probability.
                # The raw transition counts (n10, n11) are correct but
                # not directly readable -- this converts them into the
                # question a risk committee actually asks: "given a
                # breach happened yesterday, how much more likely is
                # today's breach than the unconditional rate?"
                unconditional_rate = kupiec["observed_rate"]
                denom = tm["n10"] + tm["n11"]

                print()
                print("-" * 54)
                print("Breach Analysis")
                print()
                print(
                    f"Unconditional Breach Probability : "
                    f"{unconditional_rate * 100:.2f}%"
                )

                if denom > 0:
                    conditional_rate = tm["n11"] / denom
                    print(
                        f"Conditional Breach Probability   : "
                        f"{conditional_rate * 100:.2f}%"
                    )
                    if unconditional_rate > 0:
                        multiple = conditional_rate / unconditional_rate
                        print(
                            f"Increase After Breach            : "
                            f"{multiple:.2f}x"
                        )
                else:
                    print(
                        "Conditional Breach Probability   : N/A "
                        "(no breach-after-breach observations)"
                    )

            # Real Basel backtest: worst rolling 250-day window across
            # history, not the misleading lifetime-aggregate number.
            #
            # Basel's traffic-light backtesting framework (green/yellow/
            # red exception-count thresholds over a 250-day window) is
            # explicitly defined and calibrated for 99% one-day VaR. The
            # same threshold table does not apply to 95% VaR -- running
            # it there and printing a "zone" is not a real regulatory
            # statistic, just a raw exception count wearing Basel
            # labels. So only run/print it at 99%; for other confidence
            # levels, say so explicitly instead of silently reusing
            # thresholds that don't apply.
            basel_applicable = confidence == 0.99

            print()
            if basel_applicable:
                print(f"Rolling {self.BASEL_WINDOW}-day Basel zones ({label}):")
                basel_rolling = self.rolling_basel_zones(valid, breach_col)
            else:
                print(f"Rolling Basel Analysis ({label})")
                print()
                print("Not Applicable")
                print()
                print(
                    "Basel Traffic Light is defined for 99% one-day VaR "
                    "over a rolling 250-observation backtesting window."
                )
                basel_rolling = None

            # IMPROVEMENT 3: short plain-language interpretation, built
            # from the actual test results above rather than static
            # per-confidence-level text, so it stays correct if a
            # future run passes/fails differently than this one did.
            clustering_failed = (
                christoffersen.get("passed") is False
                or conditional.get("passed") is False
            )

            worst_zone = None
            worst_date = None
            worst_exceptions = None
            if basel_rolling is not None:
                valid_windows = basel_rolling.dropna(
                    subset=["rolling_250d_exceptions"]
                )
                if not valid_windows.empty:
                    worst_row = valid_windows.loc[
                        valid_windows["rolling_250d_exceptions"].idxmax()
                    ]
                    worst_zone = worst_row["basel_zone"]
                    worst_date = worst_row["trade_date"]
                    worst_exceptions = int(worst_row["rolling_250d_exceptions"])

            print()
            print("Interpretation")
            print()

            if kupiec["passed"]:
                print(
                    f"• Kupiec test passes, indicating the overall exception "
                    f"frequency ({kupiec['observed_rate'] * 100:.2f}%) is "
                    f"consistent with the expected "
                    f"{kupiec['expected_rate'] * 100:.2f}% level."
                )
            else:
                print(
                    f"• Kupiec test fails, indicating the overall exception "
                    f"frequency ({kupiec['observed_rate'] * 100:.2f}%) "
                    f"significantly exceeds the expected "
                    f"{kupiec['expected_rate'] * 100:.2f}% level."
                )

            if clustering_failed:
                print(
                    "• Christoffersen and Conditional Coverage tests fail, "
                    "indicating exception clustering during periods of "
                    "elevated market volatility."
                )
            else:
                print(
                    "• Christoffersen and Conditional Coverage tests pass, "
                    "indicating breaches are not clustering in time."
                )

            if worst_zone == "red":
                # 2007-2009 is the conventional window for the Global
                # Financial Crisis; label it as such when the worst
                # window falls there, otherwise state the date plainly
                # rather than guessing at a named event.
                crisis_note = (
                    " (Global Financial Crisis)"
                    if worst_date is not None and 2007 <= pd.Timestamp(worst_date).year <= 2009
                    else ""
                )
                print(
                    f"• The worst rolling {self.BASEL_WINDOW}-day Basel "
                    f"window occurred during the period ending "
                    f"{worst_date}{crisis_note}, reaching the RED zone "
                    f"with {worst_exceptions} exceptions."
                )

            if clustering_failed and worst_zone == "red":
                print(
                    "• These findings indicate that Historical Simulation "
                    "VaR underestimates tail risk during rapidly changing "
                    "volatility regimes."
                )
            elif clustering_failed:
                print(
                    "• This suggests the Historical Simulation VaR adapts "
                    "too slowly during periods of changing market "
                    "volatility."
                )

            print()

    # ==========================================================
    # Run
    # ==========================================================

    def run(
        self,
        symbol: str,
    ) -> pd.DataFrame:

        print("=" * 60)
        print("SENTINEL VAR BACKTEST ENGINE")
        print("=" * 60)

        print()

        print(f"Loading {symbol}...")

        df = self.calculate(symbol)

        print(f"✓ {len(df):,} rows loaded")

        self.summary(df)

        return df


# ==========================================================
# Test
# ==========================================================

if __name__ == "__main__":

    engine = VarBacktestEngine()

    results = engine.run("SPY")

    print()

    print(results.tail())