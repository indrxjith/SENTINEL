"""
model_validation.py

Statistical backtesting suite for Value-at-Risk (VaR) models.

Implements the standard model validation tests used in market risk
management and Basel-compliant internal model validation:

    - Kupiec (1995) Proportion of Failures (POF) test
      [unconditional coverage: is the exception RATE correct?]

    - Christoffersen (1998) Independence test
      [is the TIMING of exceptions serially independent, i.e. non-clustered?]

    - Christoffersen (1998) Conditional Coverage test
      [joint test: correct rate AND independent timing]

    - Basel Traffic Light approach
      [regulatory capital multiplier zone based on 250-day exception count]

References
----------
Kupiec, P. H. (1995). "Techniques for Verifying the Accuracy of Risk
    Measurement Models." Journal of Derivatives, 3(2), 73-84.

Christoffersen, P. F. (1998). "Evaluating Interval Forecasts."
    International Economic Review, 39(4), 841-862.

Basel Committee on Banking Supervision (1996). "Supervisory Framework
    for the Use of Backtesting in Conjunction with the Internal Models
    Approach to Market Risk Capital Requirements."
"""

from __future__ import annotations

import math
from typing import Any, Dict, Optional, Sequence

import numpy as np
from scipy.stats import chi2

__all__ = ["ModelValidation"]

# Numerical floor used only to avoid a literal log(0.0) call when a count
# multiplying that term is nonzero (which should not occur analytically,
# since probabilities are estimated via MLE from the same counts, but is
# guarded against defensively for floating-point degeneracy).
_LOG_FLOOR = 1e-300


def _xlogy(n: float, p: float) -> float:
    """
    Compute ``n * ln(p)`` under the convention ``0 * ln(0) = 0``.

    This convention is not a numerical hack -- it is the mathematically
    correct treatment of likelihood terms whose multiplying count is zero.
    It follows from the limit:

        lim_{p -> 0+} p * ln(p) = 0

    which means a zero-count observation contributes nothing to the
    log-likelihood regardless of how degenerate the associated MLE
    probability is. Without this convention, likelihood terms like
    ``0 * ln(0)`` (e.g. zero breach-to-breach transitions estimated at
    probability zero) would raise a domain error despite being a
    well-defined, zero-valued term analytically.

    Parameters
    ----------
    n : float
        Count (number of observations) associated with probability ``p``.
    p : float
        Estimated probability for this term (in [0, 1]).

    Returns
    -------
    float
        The value of ``n * ln(p)``, defined as 0.0 when ``n == 0``.
    """
    if n == 0:
        return 0.0
    if p <= 0.0:
        # n > 0 but p == 0: should not occur since p is the MLE derived
        # from these same counts (p == 0 only when n == 0 too). Guarded
        # defensively rather than allowed to raise.
        return n * math.log(_LOG_FLOOR)
    return n * math.log(p)


def _validate_hit_sequence(breaches: Sequence[int]) -> np.ndarray:
    """
    Validate and coerce a breach indicator sequence to a 1-D int array.

    Parameters
    ----------
    breaches : Sequence[int]
        Sequence of 0/1 indicators, where 1 denotes a VaR exception
        (breach) on that observation date and 0 denotes no exception.

    Returns
    -------
    np.ndarray
        Validated 1-D integer array of the same values.

    Raises
    ------
    ValueError
        If the sequence is empty, not 1-D, or contains values other
        than 0 or 1.
    """
    hits = np.asarray(breaches, dtype=int)
    if hits.ndim != 1:
        raise ValueError("breaches must be a 1-D sequence")
    if hits.size == 0:
        raise ValueError("breaches sequence must be non-empty")
    if not np.all(np.isin(hits, [0, 1])):
        raise ValueError("breaches must contain only 0/1 values "
                          "(1 = VaR exception, 0 = no exception)")
    return hits


class ModelValidation:
    """
    Static-method container for VaR model backtesting statistics.

    All methods are stateless and operate purely on the hit sequence
    (and, where relevant, the model's stated confidence level) passed
    in as arguments. This keeps the validation logic independent of
    how VaR itself was computed (historical, parametric, Monte Carlo,
    filtered historical simulation, etc.), so the same suite can
    validate any VaR methodology.
    """

    # ------------------------------------------------------------------
    # Kupiec (1995) Proportion of Failures test
    # ------------------------------------------------------------------
    @staticmethod
    def kupiec_test(
        breaches: Sequence[int],
        confidence_level: float,
    ) -> Dict[str, Any]:
        """
        Kupiec (1995) Proportion of Failures (POF) test for unconditional
        coverage.

        Tests whether the OBSERVED exception rate is statistically
        consistent with the EXPECTED exception rate implied by the VaR
        model's confidence level. This test says nothing about whether
        exceptions cluster in time -- see ``christoffersen_test`` for that.

        Hypotheses
        ----------
        H0: pi_hat = p           (observed exception rate equals the
                                   rate implied by the model's confidence
                                   level, e.g. 0.05 for 95% VaR)
        H1: pi_hat != p

        Statistic
        ---------
            LR_uc = -2 * ln[ (1-p)^n0 * p^n1 / (1-pi_hat)^n0 * pi_hat^n1 ]

        where:
            n0      = number of non-exceptions
            n1      = number of exceptions
            p       = 1 - confidence_level (expected exception probability)
            pi_hat  = n1 / (n0 + n1)        (MLE of the true exception rate)

        Under H0, LR_uc ~ chi2(1) asymptotically (Wilks' theorem: the
        restricted model under H0 fixes 1 parameter to a known constant,
        vs. 1 free parameter under H1, so the difference in free
        parameters -- and hence the degrees of freedom -- is 1).

        Parameters
        ----------
        breaches : Sequence[int]
            Hit sequence: 1 where actual return breached VaR, 0 otherwise.
            Must be aligned such that VaR(t) is compared against Return(t)
            (not Return(t+1)) to avoid a lookahead/lag misalignment bug.
        confidence_level : float
            VaR confidence level, e.g. 0.95 or 0.99.

        Returns
        -------
        dict
            Structured result including the LR statistic, critical value,
            p-value, and pass/fail flag at the 95% test significance level.
        """
        if not 0.0 < confidence_level < 1.0:
            raise ValueError("confidence_level must be in (0, 1)")

        hits = _validate_hit_sequence(breaches)
        n = hits.size
        n1 = int(hits.sum())
        n0 = n - n1

        p = 1.0 - confidence_level
        pi_hat = n1 / n

        log_l_null = _xlogy(n0, 1.0 - p) + _xlogy(n1, p)
        log_l_alt = _xlogy(n0, 1.0 - pi_hat) + _xlogy(n1, pi_hat)

        lr_uc = -2.0 * (log_l_null - log_l_alt)
        # Floating point can produce a tiny negative value (e.g. -1e-14)
        # when pi_hat == p exactly; the statistic is non-negative by
        # construction (the null is nested within the alternative).
        lr_uc = max(lr_uc, 0.0)

        critical_value = float(chi2.ppf(0.95, df=1))
        p_value = float(1.0 - chi2.cdf(lr_uc, df=1))

        return {
            "test_name": "Kupiec Proportion of Failures (POF) Test",
            "n_observations": n,
            "n_exceptions": n1,
            "expected_exceptions": p * n,
            "expected_rate": p,
            "observed_rate": pi_hat,
            "lr_statistic": lr_uc,
            "degrees_of_freedom": 1,
            "critical_value": critical_value,
            "p_value": p_value,
            "passed": bool(lr_uc <= critical_value),
        }

    # ------------------------------------------------------------------
    # Christoffersen (1998) Independence test
    # ------------------------------------------------------------------
    @staticmethod
    def christoffersen_test(breaches: Sequence[int]) -> Dict[str, Any]:
        """
        Christoffersen (1998) test of independence of VaR exceptions.

        Tests whether exceptions are serially independent (i.e. whether
        the probability of an exception today depends on whether there
        was an exception yesterday). This is a first-order two-state
        Markov chain independence test -- the formulation used
        throughout Christoffersen's original 1998 paper and the version
        most commonly implemented in industry VaR backtesting suites.

        Model
        -----
        The hit sequence I_t in {0, 1} is modelled as a first-order
        Markov chain with transition matrix:

            Pi_1 = [[1 - pi01,  pi01 ],
                    [1 - pi11,  pi11 ]]

        where pi_ij = P(I_t = j | I_{t-1} = i).

        Transition counts (n_ij = count of i -> j transitions):
            n00: no-exception -> no-exception
            n01: no-exception -> exception
            n10: exception    -> no-exception
            n11: exception    -> exception

        Unrestricted MLEs:
            pi01_hat = n01 / (n00 + n01)
            pi11_hat = n11 / (n10 + n11)

        Unrestricted likelihood:
            L(Pi_1) = (1-pi01_hat)^n00 * pi01_hat^n01
                    * (1-pi11_hat)^n10 * pi11_hat^n11

        Hypotheses
        ----------
        H0: pi01 = pi11 = pi   (exceptions are serially independent --
                                 no clustering, no anti-clustering)
        H1: pi01 != pi11       (exceptions cluster in time)

        Restricted MLE under H0:
            pi_hat = (n01 + n11) / (n00 + n01 + n10 + n11)

        Restricted likelihood:
            L(Pi) = (1-pi_hat)^(n00+n10) * pi_hat^(n01+n11)

        Statistic
        ---------
            LR_ind = -2 * ln[ L(Pi) / L(Pi_1) ]

        Under H0, LR_ind ~ chi2(1) asymptotically (Wilks' theorem: the
        unrestricted model has 2 free parameters, pi01 and pi11; the
        restricted model has 1, pi; the difference of 1 gives the
        degrees of freedom).

        Edge cases
        ----------
        If either state (0 or 1) is never visited as a PREVIOUS state
        (n00+n01 == 0 or n10+n11 == 0) -- which happens when there are
        zero exceptions in the sample, or an exception on every single
        observation -- the Markov chain degenerates and independence
        cannot be meaningfully tested. In this case lr_statistic,
        p_value, and passed are returned as None/NaN rather than a
        misleading number.

        Parameters
        ----------
        breaches : Sequence[int]
            Hit sequence: 1 where actual return breached VaR, 0 otherwise.
            Must be time-ordered.

        Returns
        -------
        dict
            Structured result including the LR statistic, critical value,
            p-value, pass/fail flag, transition_matrix, and probabilities.
        """
        hits = _validate_hit_sequence(breaches)
        if hits.size < 2:
            raise ValueError(
                "need at least 2 observations to form a transition"
            )

        prev_state = hits[:-1]
        curr_state = hits[1:]

        n00 = int(np.sum((prev_state == 0) & (curr_state == 0)))
        n01 = int(np.sum((prev_state == 0) & (curr_state == 1)))
        n10 = int(np.sum((prev_state == 1) & (curr_state == 0)))
        n11 = int(np.sum((prev_state == 1) & (curr_state == 1)))

        n_from_0 = n00 + n01  # number of transitions originating in state 0
        n_from_1 = n10 + n11  # number of transitions originating in state 1
        n_total = n_from_0 + n_from_1

        pi01_hat: Optional[float] = n01 / n_from_0 if n_from_0 > 0 else None
        pi11_hat: Optional[float] = n11 / n_from_1 if n_from_1 > 0 else None
        pi_hat: Optional[float] = (
            (n01 + n11) / n_total if n_total > 0 else None
        )

        degenerate = n_from_0 == 0 or n_from_1 == 0

        if degenerate:
            lr_ind: Optional[float] = None
            p_value: Optional[float] = None
            passed: Optional[bool] = None
        else:
            log_l_unrestricted = (
                _xlogy(n00, 1.0 - pi01_hat) + _xlogy(n01, pi01_hat)
                + _xlogy(n10, 1.0 - pi11_hat) + _xlogy(n11, pi11_hat)
            )
            log_l_restricted = (
                _xlogy(n00 + n10, 1.0 - pi_hat) + _xlogy(n01 + n11, pi_hat)
            )

            lr_ind = -2.0 * (log_l_restricted - log_l_unrestricted)
            lr_ind = max(lr_ind, 0.0)
            p_value = float(1.0 - chi2.cdf(lr_ind, df=1))
            passed = bool(lr_ind <= float(chi2.ppf(0.95, df=1)))

        return {
            "test_name": "Christoffersen (1998) Independence Test",
            "lr_statistic": lr_ind,
            "degrees_of_freedom": 1,
            "critical_value": float(chi2.ppf(0.95, df=1)),
            "p_value": p_value,
            "passed": passed,
            "degenerate": degenerate,
            "transition_matrix": {
                "n00": n00, "n01": n01, "n10": n10, "n11": n11,
            },
            "probabilities": {
                "pi01_hat": pi01_hat,
                "pi11_hat": pi11_hat,
                "pi_hat": pi_hat,
            },
        }

    # ------------------------------------------------------------------
    # Christoffersen (1998) Conditional Coverage test (Kupiec + independence)
    # ------------------------------------------------------------------
    @staticmethod
    def conditional_coverage_test(
        breaches: Sequence[int],
        confidence_level: float,
    ) -> Dict[str, Any]:
        """
        Christoffersen (1998) joint test of conditional coverage.

        Combines the unconditional coverage test (Kupiec) and the
        independence test (Christoffersen) into a single joint test of
        whether the VaR model produces exceptions at the CORRECT RATE
        and INDEPENDENTLY over time. This is the most complete single
        backtest and the one most commonly reported by internal model
        validation teams, since a model can pass either component test
        individually while failing the joint hypothesis.

        Statistic
        ---------
        Because the two likelihood ratio statistics are asymptotically
        independent under their respective nulls, they are additive:

            LR_cc = LR_uc + LR_ind  ~  chi2(2) under H0

        Hypotheses
        ----------
        H0: exception rate is correct AND exceptions are independent
        H1: exception rate is incorrect OR exceptions are dependent
            (or both)

        Parameters
        ----------
        breaches : Sequence[int]
            Hit sequence: 1 where actual return breached VaR, 0 otherwise.
        confidence_level : float
            VaR confidence level, e.g. 0.95 or 0.99.

        Returns
        -------
        dict
            Structured result including the joint LR statistic, critical
            value, p-value, pass/fail flag, and the two component test
            results for diagnostic purposes.
        """
        uc_result = ModelValidation.kupiec_test(breaches, confidence_level)
        ind_result = ModelValidation.christoffersen_test(breaches)

        if ind_result["lr_statistic"] is None:
            lr_cc: Optional[float] = None
            p_value: Optional[float] = None
            passed: Optional[bool] = None
        else:
            lr_cc = uc_result["lr_statistic"] + ind_result["lr_statistic"]
            p_value = float(1.0 - chi2.cdf(lr_cc, df=2))
            passed = bool(lr_cc <= float(chi2.ppf(0.95, df=2)))

        return {
            "test_name": "Christoffersen (1998) Conditional Coverage Test",
            "lr_statistic": lr_cc,
            "degrees_of_freedom": 2,
            "critical_value": float(chi2.ppf(0.95, df=2)),
            "p_value": p_value,
            "passed": passed,
            "components": {
                "unconditional_coverage": uc_result,
                "independence": ind_result,
            },
        }

    # ------------------------------------------------------------------
    # Basel Traffic Light approach
    # ------------------------------------------------------------------
    @staticmethod
    def basel_traffic_light(
        n_exceptions: int,
        n_observations: int = 250,
    ) -> Dict[str, Any]:
        """
        Basel Committee (1996) traffic-light backtesting approach.

        Classifies a VaR model's 99% 1-day backtest performance over a
        (typically 250-observation, i.e. one trading year) window into
        Green / Yellow / Red zones, each carrying a prescribed capital
        multiplier used to scale the regulatory capital requirement.

        Standard boundaries (defined for a 250-observation window at the
        99% confidence level, per the original Basel framework):

            Green  zone: 0-4   exceptions -> multiplier 3.00 (no penalty)
            Yellow zone: 5-9   exceptions -> multiplier 3.40-3.85
                                              (increasing penalty)
            Red    zone: 10+   exceptions -> multiplier 4.00 (maximum
                                              penalty, model presumed
                                              deficient)

        Note
        ----
        These exact exception-count boundaries and multipliers are only
        rigorously defined for n_observations == 250 at the 99% level.
        For other window lengths, this implementation scales the
        boundaries proportionally as an approximation; a production
        deployment backtesting a non-standard window should instead
        recompute exact boundaries from the cumulative binomial
        distribution at that window length and confidence level.

        Parameters
        ----------
        n_exceptions : int
            Number of VaR exceptions observed in the window.
        n_observations : int, default 250
            Number of observations in the backtesting window.

        Returns
        -------
        dict
            Structured result including the assigned zone and capital
            multiplier.
        """
        if n_observations <= 0:
            raise ValueError("n_observations must be positive")
        if n_exceptions < 0:
            raise ValueError("n_exceptions cannot be negative")

        scale = n_observations / 250.0
        green_max = 4 * scale
        yellow_max = 9 * scale

        # Standard Basel multiplier schedule for the 5-9 exception
        # (yellow) zone at the canonical 250-day window.
        yellow_multipliers = {
            5: 3.40, 6: 3.50, 7: 3.65, 8: 3.75, 9: 3.85,
        }

        if n_exceptions <= green_max:
            zone = "green"
            multiplier = 3.00
        elif n_exceptions <= yellow_max:
            zone = "yellow"
            # Map back to the canonical 250-day exception bucket for the
            # multiplier lookup when the window has been scaled.
            bucket = int(round(n_exceptions / scale)) if scale > 0 else n_exceptions
            bucket = min(9, max(5, bucket))
            multiplier = yellow_multipliers[bucket]
        else:
            zone = "red"
            multiplier = 4.00

        return {
            "test_name": "Basel Traffic Light Backtesting Approach",
            "n_exceptions": n_exceptions,
            "n_observations": n_observations,
            "zone": zone,
            "capital_multiplier": multiplier,
            "green_zone_max_exceptions": green_max,
            "yellow_zone_max_exceptions": yellow_max,
        }


# ==========================================================
# Test
# ==========================================================

if __name__ == "__main__":

    # Example breach sequence
    hits = [0] * 6080 + [1] * 329

    # ------------------------------------------------------
    # Kupiec Test
    # ------------------------------------------------------

    kupiec = ModelValidation.kupiec_test(
        breaches=hits,
        confidence_level=0.95,
    )

    print("\n" + "=" * 70)
    print(kupiec["test_name"])
    print("=" * 70)

    for key, value in kupiec.items():
        if key != "test_name":
            print(f"{key:<25}: {value}")

    # ------------------------------------------------------
    # Christoffersen Test
    # ------------------------------------------------------

    christoffersen = ModelValidation.christoffersen_test(
        breaches=hits,
    )

    print("\n" + "=" * 70)
    print(christoffersen["test_name"])
    print("=" * 70)

    for key, value in christoffersen.items():
        if key != "test_name":
            print(f"{key:<25}: {value}")

    # ------------------------------------------------------
    # Conditional Coverage
    # ------------------------------------------------------

    conditional = ModelValidation.conditional_coverage_test(
        breaches=hits,
        confidence_level=0.95,
    )

    print("\n" + "=" * 70)
    print(conditional["test_name"])
    print("=" * 70)

    for key, value in conditional.items():
        if key != "test_name":
            print(f"{key:<25}: {value}")

    # ------------------------------------------------------
    # Basel Traffic Light
    # ------------------------------------------------------

    basel = ModelValidation.basel_traffic_light(
        n_exceptions=4,
        n_observations=250,
    )

    print("\n" + "=" * 70)
    print(basel["test_name"])
    print("=" * 70)

    for key, value in basel.items():
        if key != "test_name":
            print(f"{key:<25}: {value}")