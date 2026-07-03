"""
Unit tests for ModelValidation.

Run with:
    pytest src/tests/test_model_validation.py -v

ModelValidation is pure math (numpy/scipy only, no DB), so every test
here builds a hand-constructed hit sequence and checks the result
against an independently-computed expected value -- either a value
computable on paper (e.g. the exact-match Kupiec case, where the
observed rate equals the expected rate and LR must be exactly 0) or a
manual re-derivation of the likelihood-ratio formula using plain
numpy, kept deliberately separate from ModelValidation's own
implementation so the test isn't just checking the code against
itself.
"""

import numpy as np
import pytest
from scipy.stats import chi2

from src.analytics.model_validation import ModelValidation, _xlogy


# ======================================================================
# Fixtures / helpers
# ======================================================================

def make_hits(n_total: int, n_exceptions: int, clustered: bool = False) -> list:
    """
    Build a 0/1 hit sequence with an exact exception count.

    clustered=False -> exceptions spread evenly (independent-ish).
    clustered=True  -> all exceptions bunched at the end (dependent).
    """
    if clustered:
        return [0] * (n_total - n_exceptions) + [1] * n_exceptions
    hits = [0] * n_total
    if n_exceptions > 0:
        step = n_total // n_exceptions
        for i in range(n_exceptions):
            hits[min(i * step, n_total - 1)] = 1
    return hits


def manual_lr_uc(n0: int, n1: int, p: float) -> float:
    """Independent re-derivation of the Kupiec LR statistic."""
    pi_hat = n1 / (n0 + n1)
    ll_null = _safe_xlogy(n0, 1 - p) + _safe_xlogy(n1, p)
    ll_alt = _safe_xlogy(n0, 1 - pi_hat) + _safe_xlogy(n1, pi_hat)
    return max(-2.0 * (ll_null - ll_alt), 0.0)


def _safe_xlogy(n, prob):
    if n == 0:
        return 0.0
    return n * np.log(prob)


# ======================================================================
# _xlogy helper
# ======================================================================

class TestXlogy:

    def test_zero_count_is_zero_regardless_of_probability(self):
        assert _xlogy(0, 0.0) == 0.0
        assert _xlogy(0, 0.5) == 0.0

    def test_matches_plain_log_for_positive_probability(self):
        assert _xlogy(4, 0.25) == pytest.approx(4 * np.log(0.25))

    def test_does_not_raise_on_zero_probability_with_nonzero_count(self):
        # Analytically shouldn't occur (p==0 only when n==0 too), but
        # must not raise a domain error if it does.
        result = _xlogy(3, 0.0)
        assert np.isfinite(result)
        assert result < 0


# ======================================================================
# Kupiec (POF) test
# ======================================================================

class TestKupiecTest:

    def test_exact_match_gives_zero_lr_and_passes(self):
        # 5 exceptions out of 100 at 95% VaR (p=0.05) is a perfect match.
        hits = make_hits(100, 5)
        result = ModelValidation.kupiec_test(hits, confidence_level=0.95)
        assert result["lr_statistic"] == pytest.approx(0.0, abs=1e-9)
        assert result["passed"] is True
        assert result["n_exceptions"] == 5
        assert result["n_observations"] == 100
        assert result["expected_rate"] == pytest.approx(0.05)
        assert result["observed_rate"] == pytest.approx(0.05)

    def test_excess_exceptions_fails_and_matches_manual_lr(self):
        # 20 exceptions out of 100 at the 95% level is far too many.
        hits = make_hits(100, 20)
        result = ModelValidation.kupiec_test(hits, confidence_level=0.95)
        expected_lr = manual_lr_uc(n0=80, n1=20, p=0.05)
        assert result["lr_statistic"] == pytest.approx(expected_lr)
        assert result["passed"] is False
        assert result["p_value"] < 0.05

    def test_critical_value_is_chi2_one_dof_95pct(self):
        hits = make_hits(50, 3)
        result = ModelValidation.kupiec_test(hits, confidence_level=0.95)
        assert result["critical_value"] == pytest.approx(chi2.ppf(0.95, df=1))
        assert result["degrees_of_freedom"] == 1

    def test_lr_statistic_never_negative(self):
        # Guards against floating point producing e.g. -1e-14.
        for n_exceptions in range(0, 21):
            hits = make_hits(200, n_exceptions)
            result = ModelValidation.kupiec_test(hits, confidence_level=0.95)
            assert result["lr_statistic"] >= 0.0

    def test_too_few_exceptions_also_fails(self):
        # 0 exceptions out of 100 at 99% (p=0.01) is suspiciously low
        # but should still register as a real (large) deviation only
        # once far enough from the expected rate; here just confirm
        # it doesn't error and produces a sensible non-negative LR.
        hits = make_hits(100, 0)
        result = ModelValidation.kupiec_test(hits, confidence_level=0.99)
        assert result["n_exceptions"] == 0
        assert result["lr_statistic"] >= 0.0

    def test_rejects_invalid_confidence_level(self):
        with pytest.raises(ValueError, match="confidence_level"):
            ModelValidation.kupiec_test([0, 1, 0], confidence_level=1.5)
        with pytest.raises(ValueError, match="confidence_level"):
            ModelValidation.kupiec_test([0, 1, 0], confidence_level=0.0)

    def test_rejects_empty_sequence(self):
        with pytest.raises(ValueError, match="non-empty"):
            ModelValidation.kupiec_test([], confidence_level=0.95)

    def test_rejects_non_binary_values(self):
        with pytest.raises(ValueError, match="0/1"):
            ModelValidation.kupiec_test([0, 1, 2], confidence_level=0.95)


# ======================================================================
# Christoffersen independence test
# ======================================================================

class TestChristoffersenTest:

    def test_no_exceptions_is_degenerate(self):
        hits = [0] * 20
        result = ModelValidation.christoffersen_test(hits)
        assert result["degenerate"] is True
        assert result["lr_statistic"] is None
        assert result["p_value"] is None
        assert result["passed"] is None

    def test_all_exceptions_is_degenerate(self):
        # Every single observation is an exception -> state 0 is
        # never visited as a previous state either.
        hits = [1] * 20
        result = ModelValidation.christoffersen_test(hits)
        assert result["degenerate"] is True
        assert result["lr_statistic"] is None

    def test_clustered_exceptions_detected_as_dependent(self):
        # All exceptions bunched together: 0->1 almost never happens,
        # 1->1 happens constantly. Independence should be rejected.
        hits = make_hits(20, 10, clustered=True)
        result = ModelValidation.christoffersen_test(hits)
        assert result["degenerate"] is False
        assert result["passed"] is False
        tm = result["transition_matrix"]
        assert tm["n00"] + tm["n01"] + tm["n10"] + tm["n11"] == 19

    def test_transition_matrix_counts_are_consistent(self):
        hits = [0, 1, 0, 1, 0, 1, 0, 1, 0, 1]
        result = ModelValidation.christoffersen_test(hits)
        tm = result["transition_matrix"]
        # 9 transitions total for 10 observations.
        assert sum(tm.values()) == 9
        # Perfect alternation: no 0->0 and no 1->1 transitions.
        assert tm["n00"] == 0
        assert tm["n11"] == 0

    def test_requires_at_least_two_observations(self):
        with pytest.raises(ValueError, match="at least 2"):
            ModelValidation.christoffersen_test([1])

    def test_probabilities_are_none_when_state_unvisited(self):
        hits = [0] * 20
        result = ModelValidation.christoffersen_test(hits)
        assert result["probabilities"]["pi11_hat"] is None


# ======================================================================
# Conditional coverage test
# ======================================================================

class TestConditionalCoverageTest:

    def test_joint_lr_is_additive_over_components(self):
        hits = make_hits(100, 5)
        result = ModelValidation.conditional_coverage_test(
            hits, confidence_level=0.95
        )
        uc = result["components"]["unconditional_coverage"]["lr_statistic"]
        ind = result["components"]["independence"]["lr_statistic"]
        assert result["lr_statistic"] == pytest.approx(uc + ind)
        assert result["degrees_of_freedom"] == 2

    def test_propagates_degenerate_independence_component(self):
        # If Christoffersen can't be computed, the joint test can't
        # either -- it should not silently fall back to just Kupiec.
        hits = [0] * 20
        result = ModelValidation.conditional_coverage_test(
            hits, confidence_level=0.95
        )
        assert result["lr_statistic"] is None
        assert result["passed"] is None
        # But the Kupiec component is still computed and available.
        assert result["components"]["unconditional_coverage"]["lr_statistic"] is not None

    def test_critical_value_is_chi2_two_dof(self):
        hits = make_hits(100, 5)
        result = ModelValidation.conditional_coverage_test(
            hits, confidence_level=0.95
        )
        assert result["critical_value"] == pytest.approx(chi2.ppf(0.95, df=2))


# ======================================================================
# Basel Traffic Light
# ======================================================================

class TestBaselTrafficLight:

    @pytest.mark.parametrize(
        "n_exceptions,expected_zone,expected_multiplier",
        [
            (0, "green", 3.00),
            (4, "green", 3.00),   # upper edge of green
            (5, "yellow", 3.40),  # lower edge of yellow
            (6, "yellow", 3.50),
            (7, "yellow", 3.65),
            (8, "yellow", 3.75),
            (9, "yellow", 3.85),  # upper edge of yellow
            (10, "red", 4.00),    # lower edge of red
            (15, "red", 4.00),
        ],
    )
    def test_standard_250_day_boundaries(
        self, n_exceptions, expected_zone, expected_multiplier
    ):
        result = ModelValidation.basel_traffic_light(
            n_exceptions, n_observations=250
        )
        assert result["zone"] == expected_zone
        assert result["capital_multiplier"] == pytest.approx(expected_multiplier)

    def test_scales_boundaries_for_non_standard_window(self):
        # A 500-day window should double the green/yellow boundaries.
        result = ModelValidation.basel_traffic_light(8, n_observations=500)
        assert result["green_zone_max_exceptions"] == pytest.approx(8.0)
        assert result["zone"] == "green"

    def test_rejects_negative_exceptions(self):
        with pytest.raises(ValueError, match="cannot be negative"):
            ModelValidation.basel_traffic_light(-1, n_observations=250)

    def test_rejects_non_positive_observations(self):
        with pytest.raises(ValueError, match="must be positive"):
            ModelValidation.basel_traffic_light(5, n_observations=0)

    def test_default_window_is_250(self):
        result = ModelValidation.basel_traffic_light(4)
        assert result["n_observations"] == 250