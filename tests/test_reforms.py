"""Tests for the co_tax_calc.reforms module.

Verify the FORWARD Initiative 195 reform definition (single contrib
flag from 2027), the pin annotation, and the hand-computable bracket
math used to cross-check the model.
"""

import pytest
from co_tax_calc.reforms import (
    BASELINE_FLAT_RATE,
    BRACKETS,
    POLICYENGINE_US_PIN,
    REFORM_PARAMS,
    create_co_reform,
    graduated_tax,
)


class TestReformParams:
    """Tests for the REFORM_PARAMS contrib-flag override."""

    def test_single_parameter(self):
        """Initiative 195 is a single contrib flag — nothing else."""
        assert list(REFORM_PARAMS.keys()) == [
            "gov.contrib.states.co.progressive_income_tax.in_effect"
        ]

    def test_effective_2027_forward(self):
        periods = REFORM_PARAMS[
            "gov.contrib.states.co.progressive_income_tax.in_effect"
        ]
        assert periods == {"2027-01-01.2100-12-31": True}

    def test_structure_for_policyengine(self):
        """Structure must be compatible with Reform.from_dict()."""
        for param_path, periods in REFORM_PARAMS.items():
            assert isinstance(param_path, str)
            assert isinstance(periods, dict)
            for period_str in periods:
                start, end = period_str.split(".")
                assert len(start) == 10
                assert len(end) == 10


class TestPin:
    """The pin must be exact (==) and reference policyengine-us."""

    def test_exact_pin(self):
        name, _, version = POLICYENGINE_US_PIN.partition("==")
        assert name == "policyengine-us"
        assert version, "pin must be exact (policyengine-us==X.Y.Z)"
        # First release containing PR #9431.
        major, minor, patch = (int(p) for p in version.split("."))
        assert (major, minor, patch) >= (1, 825, 0)


class TestCreateCoReform:
    """Tests for create_co_reform()."""

    def test_returns_reform(self):
        reform = create_co_reform()
        from policyengine_core.reforms import Reform

        assert isinstance(reform, type)
        assert issubclass(reform, Reform)


class TestBrackets:
    """Tests for the Initiative 195 bracket constants and math."""

    def test_six_brackets(self):
        assert len(BRACKETS) == 6

    def test_bracket_schedule(self):
        assert BRACKETS == [
            (0, 0.037),
            (25_000, 0.042),
            (100_000, 0.044),
            (500_000, 0.074),
            (750_000, 0.079),
            (1_000_000, 0.084),
        ]

    def test_baseline_flat_rate(self):
        assert BASELINE_FLAT_RATE == 0.044

    def test_graduated_tax_at_300k(self):
        """$300k taxable: 25k*3.7% + 75k*4.2% + 200k*4.4% = $12,875."""
        assert graduated_tax(300_000) == pytest.approx(12_875)

    def test_graduated_tax_at_zero(self):
        assert graduated_tax(0) == 0.0

    def test_graduated_tax_first_bracket(self):
        assert graduated_tax(20_000) == pytest.approx(20_000 * 0.037)

    def test_graduated_tax_above_1m(self):
        """$1.5M: 925 + 3,150 + 17,600 + 18,500 + 19,750 + 42,000."""
        expected = (
            25_000 * 0.037
            + 75_000 * 0.042
            + 400_000 * 0.044
            + 250_000 * 0.074
            + 250_000 * 0.079
            + 500_000 * 0.084
        )
        assert graduated_tax(1_500_000) == pytest.approx(expected)

    def test_cut_below_100k_increase_above_500k(self):
        """Vs the 4.4% flat tax: cut below $100k, increase above $500k."""
        assert graduated_tax(80_000) < 80_000 * BASELINE_FLAT_RATE
        assert graduated_tax(300_000) < 300_000 * BASELINE_FLAT_RATE
        assert graduated_tax(600_000) > 600_000 * BASELINE_FLAT_RATE
        assert graduated_tax(1_200_000) > 1_200_000 * BASELINE_FLAT_RATE
