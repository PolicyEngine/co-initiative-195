"""Tests for the co_tax_calc.household module.

Verify that the household-situation builder produces correct
PolicyEngine-compatible dictionaries, defaulting to Colorado (CO) for
this dashboard.
"""

from co_tax_calc.household import (
    DEFAULT_MAX_EARNINGS,
    build_household_situation,
)


class TestBuildHouseholdSituation:
    """Tests for build_household_situation()."""

    def test_default_state_is_colorado(self):
        """state_code defaults to CO when not specified."""
        situation = build_household_situation(
            age_head=28,
            age_spouse=None,
            dependent_ages=[],
            income=45000,
            year=2027,
            include_axes=False,
        )
        assert (
            situation["households"]["your household"]["state_code"]["2027"]
            == "CO"
        )

    def test_default_max_earnings_covers_top_bracket(self):
        """The default sweep must extend past $1M (top 8.4% bracket)."""
        assert DEFAULT_MAX_EARNINGS >= 1_200_000

    def test_single_filer(self):
        situation = build_household_situation(
            age_head=28,
            age_spouse=None,
            dependent_ages=[],
            income=45000,
            year=2027,
            max_earnings=1300000,
            state_code="CO",
            include_axes=False,
        )

        assert len(situation["people"]) == 1
        assert situation["people"]["you"]["age"]["2027"] == 28
        assert "your partner" not in situation["people"]

    def test_single_parent_with_one_child(self):
        situation = build_household_situation(
            age_head=30,
            age_spouse=None,
            dependent_ages=[2],
            income=20000,
            year=2027,
            max_earnings=1300000,
            state_code="CO",
            include_axes=False,
        )

        assert "you" in situation["people"]
        assert "your first dependent" in situation["people"]
        assert situation["people"]["your first dependent"]["age"]["2027"] == 2
        assert "your partner" not in situation["people"]

    def test_married_couple_with_two_children(self):
        situation = build_household_situation(
            age_head=40,
            age_spouse=38,
            dependent_ages=[6, 9],
            income=95000,
            year=2027,
            max_earnings=1300000,
            state_code="CO",
            include_axes=False,
        )

        assert "you" in situation["people"]
        assert "your partner" in situation["people"]
        assert situation["people"]["your partner"]["age"]["2027"] == 38
        assert "your first dependent" in situation["people"]
        assert "your second dependent" in situation["people"]

        members = situation["tax_units"]["your tax unit"]["members"]
        assert "you" in members
        assert "your partner" in members
        assert "your first dependent" in members
        assert "your second dependent" in members

    def test_three_plus_children(self):
        situation = build_household_situation(
            age_head=35,
            age_spouse=33,
            dependent_ages=[0, 1, 2, 3],
            income=35000,
            year=2027,
            max_earnings=1300000,
            state_code="CO",
            include_axes=False,
        )

        assert "your first dependent" in situation["people"]
        assert "your second dependent" in situation["people"]
        assert "dependent_3" in situation["people"]
        assert "dependent_4" in situation["people"]

    def test_axes_included(self):
        situation = build_household_situation(
            age_head=30,
            age_spouse=None,
            dependent_ages=[2],
            income=20000,
            year=2027,
            max_earnings=1300000,
            state_code="CO",
            include_axes=True,
        )

        assert "axes" in situation
        assert len(situation["axes"]) == 1
        assert len(situation["axes"][0]) == 1

        axis = situation["axes"][0][0]
        assert axis["name"] == "employment_income"
        assert axis["min"] == 0
        assert axis["max"] == 1300000
        assert axis["period"] == "2027"

    def test_axes_excluded(self):
        situation = build_household_situation(
            age_head=30,
            age_spouse=None,
            dependent_ages=[2],
            income=20000,
            year=2027,
            max_earnings=1300000,
            state_code="CO",
            include_axes=False,
        )
        assert "axes" not in situation

    def test_axis_max_uses_higher_of_income_or_max_earnings(self):
        """Axis maximum is the larger of income and max_earnings."""
        situation_high_income = build_household_situation(
            age_head=30,
            age_spouse=None,
            dependent_ages=[],
            income=2000000,
            year=2027,
            max_earnings=1300000,
            state_code="CO",
            include_axes=True,
        )
        assert situation_high_income["axes"][0][0]["max"] == 2000000

        situation_high_max = build_household_situation(
            age_head=30,
            age_spouse=None,
            dependent_ages=[],
            income=100000,
            year=2027,
            max_earnings=1300000,
            state_code="CO",
            include_axes=True,
        )
        assert situation_high_max["axes"][0][0]["max"] == 1300000

    def test_marital_units_created_correctly(self):
        """Each child gets their own marital unit."""
        situation = build_household_situation(
            age_head=35,
            age_spouse=None,
            dependent_ages=[5, 10],
            income=50000,
            year=2027,
            max_earnings=1300000,
            state_code="CO",
            include_axes=False,
        )

        assert "your marital unit" in situation["marital_units"]
        assert (
            "you" in situation["marital_units"]["your marital unit"]["members"]
        )
        assert "your first dependent's marital unit" in situation["marital_units"]
        assert "your second dependent's marital unit" in situation["marital_units"]
