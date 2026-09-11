"""Tests for the precomputed CSV data files.

Verify that the CSV files match scripts/DATA_SCHEMA.md so they can be
parsed by the frontend. Tax year 2027 (Initiative 195's first year) is
the only year in this dashboard. Files are produced by the Modal
pipelines; tests skip when a file has not been generated yet.
"""

import csv
from pathlib import Path

import pytest

DATA_DIR = Path(__file__).parent.parent / "frontend" / "public" / "data"
EXPECTED_YEARS = [2027]
EXPECTED_BRACKETS = {
    "$0 - $25k",
    "$25k - $50k",
    "$50k - $75k",
    "$75k - $100k",
    "$100k - $200k",
    "$200k - $500k",
    "$500k - $750k",
    "$750k - $1M",
    "$1M+",
}


class TestDistributionalImpactCSV:
    """Tests for distributional_impact.csv."""

    @pytest.fixture
    def data(self):
        filepath = DATA_DIR / "distributional_impact.csv"
        if not filepath.exists():
            pytest.skip("distributional_impact.csv not generated yet")
        with open(filepath, "r") as f:
            return list(csv.DictReader(f))

    def test_has_required_columns(self, data):
        required = ["year", "decile", "average_change", "relative_change"]
        for row in data:
            for col in required:
                assert col in row, f"Missing column: {col}"

    def test_has_all_deciles(self, data):
        for year in EXPECTED_YEARS:
            year_data = [r for r in data if int(r["year"]) == year]
            deciles = {r["decile"] for r in year_data}
            expected = {str(d) for d in range(1, 11)}
            assert deciles == expected, f"Missing deciles for year {year}"

    def test_values_are_numeric(self, data):
        for row in data:
            float(row["year"])
            float(row["average_change"])
            float(row["relative_change"])


class TestMetricsCSV:
    """Tests for metrics.csv."""

    @pytest.fixture
    def data(self):
        filepath = DATA_DIR / "metrics.csv"
        if not filepath.exists():
            pytest.skip("metrics.csv not generated yet")
        with open(filepath, "r") as f:
            return list(csv.DictReader(f))

    def test_has_required_columns(self, data):
        required = ["year", "metric", "value"]
        for row in data:
            for col in required:
                assert col in row, f"Missing column: {col}"

    def test_has_required_metrics(self, data):
        required_metrics = [
            "budgetary_impact",
            "state_tax_revenue_impact",
            "federal_tax_revenue_impact",
            "households",
            "avg_household_net_income_change",
            "winners",
            "losers",
            "winners_rate",
            "losers_rate",
            "poverty_baseline_rate",
            "poverty_reform_rate",
        ]
        for year in EXPECTED_YEARS:
            year_data = [r for r in data if int(r["year"]) == year]
            metrics = {r["metric"] for r in year_data}
            for metric in required_metrics:
                assert metric in metrics, (
                    f"Missing metric '{metric}' for year {year}"
                )

    def test_state_revenue_impact_is_positive(self, data):
        """Initiative 195 raises CO income-tax revenue on net (the
        graduated top rates above $500k dominate the sub-$100k cuts).
        A negative value indicates a flipped sign convention."""
        rows = [
            r for r in data if r["metric"] == "state_tax_revenue_impact"
        ]
        assert rows, "state_tax_revenue_impact missing"
        for row in rows:
            assert float(row["value"]) > 0, (
                "state_tax_revenue_impact should be positive "
                "(reform - baseline revenue); sign convention may be "
                "flipped"
            )


class TestWinnersLosersCSV:
    """Tests for winners_losers.csv."""

    @pytest.fixture
    def data(self):
        filepath = DATA_DIR / "winners_losers.csv"
        if not filepath.exists():
            pytest.skip("winners_losers.csv not generated yet")
        with open(filepath, "r") as f:
            return list(csv.DictReader(f))

    def test_has_required_columns(self, data):
        required = [
            "year", "decile",
            "gain_more_5pct", "gain_less_5pct", "no_change",
            "lose_less_5pct", "lose_more_5pct",
        ]
        for row in data:
            for col in required:
                assert col in row, f"Missing column: {col}"

    def test_has_all_deciles_and_all(self, data):
        for year in EXPECTED_YEARS:
            year_data = [r for r in data if int(r["year"]) == year]
            deciles = {r["decile"] for r in year_data}
            expected = {"All"} | {str(d) for d in range(1, 11)}
            assert deciles == expected, f"Missing deciles for year {year}"

    def test_values_sum_to_one(self, data):
        for row in data:
            total = (
                float(row["gain_more_5pct"])
                + float(row["gain_less_5pct"])
                + float(row["no_change"])
                + float(row["lose_less_5pct"])
                + float(row["lose_more_5pct"])
            )
            assert abs(total - 1.0) < 0.01, f"Row does not sum to 1: {row}"


class TestIncomeBracketsCSV:
    """Tests for income_brackets.csv."""

    @pytest.fixture
    def data(self):
        filepath = DATA_DIR / "income_brackets.csv"
        if not filepath.exists():
            pytest.skip("income_brackets.csv not generated yet")
        with open(filepath, "r") as f:
            return list(csv.DictReader(f))

    def test_has_required_columns(self, data):
        required = [
            "year",
            "bracket",
            "households",
            "beneficiaries",
            "total_cost",
            "avg_benefit",
        ]
        for row in data:
            for col in required:
                assert col in row, f"Missing column: {col}"

    def test_has_all_brackets(self, data):
        for year in EXPECTED_YEARS:
            year_data = [r for r in data if int(r["year"]) == year]
            brackets = {r["bracket"] for r in year_data}
            assert brackets == EXPECTED_BRACKETS, (
                f"Missing brackets for year {year}"
            )

    def test_top_band_pays_more(self, data):
        """$1M+ households face the 7.4%-8.4% rates: their average
        net-income change must be negative (they pay more tax)."""
        top = [r for r in data if r["bracket"] == "$1M+"]
        assert top, "$1M+ band missing"
        for row in top:
            assert float(row["avg_benefit"]) < 0, (
                "$1M+ avg_benefit should be negative under Initiative "
                "195; sign convention may be flipped"
            )


class TestCongressionalDistrictsCSV:
    """Tests for congressional_districts.csv (Colorado only)."""

    @pytest.fixture
    def data(self):
        filepath = DATA_DIR / "congressional_districts.csv"
        if not filepath.exists():
            pytest.skip("congressional_districts.csv not generated yet")
        with open(filepath, "r") as f:
            return list(csv.DictReader(f))

    def test_has_required_columns(self, data):
        required = [
            "district",
            "average_household_income_change",
            "relative_household_income_change",
            "winners_share",
            "losers_share",
            "affected_share",
            "state_revenue_impact",
            "poverty_pct_change",
            "child_poverty_pct_change",
            "state",
            "year",
        ]
        for row in data:
            for col in required:
                assert col in row, f"Missing column: {col}"

    def test_colorado_only(self, data):
        """All rows must be Colorado districts."""
        states = {r["state"] for r in data}
        assert states == {"CO"}, f"Expected only CO rows, got {states}"

    def test_eight_districts(self, data):
        """Colorado has 8 congressional districts."""
        districts = {r["district"] for r in data}
        expected = {f"CO-0{d}" for d in range(1, 9)}
        assert districts == expected, (
            f"Expected Colorado districts CO-01..CO-08, got {districts}"
        )

    def test_single_year_2027(self, data):
        years = {int(r["year"]) for r in data}
        assert years == {2027}, f"Expected only 2027, got {years}"

    def test_affected_share_consistent(self, data):
        for row in data:
            expected = float(row["winners_share"]) + float(row["losers_share"])
            assert abs(float(row["affected_share"]) - expected) < 0.001


class TestGeojson:
    """The committed national geojson must cover all 8 CO districts."""

    @pytest.mark.parametrize(
        "filename,id_key",
        [
            ("congressional_districts.geojson", "DISTRICT_ID"),
            ("congressional_districts_hex.geojson", "DISTRICT_ID"),
        ],
    )
    def test_co_districts_present(self, filename, id_key):
        import json

        filepath = DATA_DIR / "geojson" / filename
        assert filepath.exists(), f"{filename} missing"
        with open(filepath, "r", encoding="utf-8") as f:
            geo = json.load(f)
        ids = {
            feat["properties"].get(id_key)
            for feat in geo["features"]
        }
        expected = {f"CO-0{d}" for d in range(1, 9)}
        assert expected <= ids, (
            f"{filename} missing CO districts: {expected - ids}"
        )
