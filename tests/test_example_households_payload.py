"""Schema validation for the precomputed example_households.json payload.

The dashboard's "Example households" cards and sweep chart read this
file directly; a typo in ``scripts/compute_example_households.py``
(dropping a key, renaming a field, flipping a sign) would silently
produce broken UI without these tests.

Pure schema checks against the committed JSON -- they do not re-run any
PolicyEngine sims. Schema: scripts/DATA_SCHEMA.md.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

PAYLOAD_PATH = (
    Path(__file__).resolve().parent.parent
    / "frontend"
    / "public"
    / "data"
    / "example_households.json"
)


@pytest.fixture(scope="module")
def payload() -> dict:
    if not PAYLOAD_PATH.exists():
        pytest.skip("example_households.json not generated yet")
    with PAYLOAD_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def households(payload: dict) -> list[dict]:
    return payload["households"]


def test_top_level_shape(payload: dict) -> None:
    assert payload["year"] == 2027
    assert payload["pin"].startswith("policyengine-us==")
    assert isinstance(payload["households"], list)
    assert len(payload["households"]) >= 3


def test_profile_fields_present(households: list[dict]) -> None:
    required = {"label", "income", "age_head", "married", "dependents"}
    for h in households:
        assert required <= h.keys(), (
            f"household {h.get('label')} missing fields: {required - h.keys()}"
        )


def test_baseline_and_reform_fields(households: list[dict]) -> None:
    required = {"household_net_income", "co_income_tax", "income_tax"}
    for h in households:
        for key in ("baseline", "reform"):
            assert required <= h[key].keys(), (
                f"household {h['label']}/{key} missing fields: "
                f"{required - h[key].keys()}"
            )


def test_top_level_changes_present(households: list[dict]) -> None:
    for h in households:
        for key in ("net_income_change", "state_tax_change", "federal_tax_change"):
            assert key in h, f"household {h['label']} missing '{key}'"
            assert isinstance(h[key], (int, float))


def test_no_ga_provision_keys(households: list[dict]) -> None:
    """Initiative 195 is a single provision -- the GA template's
    per-provision attribution keys must be gone."""
    for h in households:
        assert "provisions" not in h
        assert "provisions_chart" not in h


def test_chart_arrays_aligned(households: list[dict]) -> None:
    """All chart arrays must have the same length as income_range."""
    for h in households:
        chart = h["chart"]
        n = len(chart["income_range"])
        assert n > 1, f"household {h['label']} chart.income_range too short"
        for key in ("net_income_change", "state_tax_change", "federal_tax_change"):
            assert len(chart[key]) == n, (
                f"household {h['label']} chart.{key} has {len(chart[key])} "
                f"entries vs income_range {n}"
            )


def test_sweep_reaches_1_3m(households: list[dict]) -> None:
    """The income sweep must reach $1.3M so all six brackets show."""
    for h in households:
        assert max(h["chart"]["income_range"]) >= 1_300_000 - 1, (
            f"household {h['label']} sweep tops out at "
            f"{max(h['chart']['income_range'])}"
        )


def test_includes_millionaire_profile(households: list[dict]) -> None:
    """At least one profile must earn > $1M (top 8.4% bracket)."""
    assert any(h["income"] > 1_000_000 for h in households)


def test_sign_convention_millionaire_pays_more(
    households: list[dict],
) -> None:
    """A >$1M household must pay MORE CO tax under Initiative 195
    (positive tax-side state_tax_change, negative net_income_change)."""
    for h in households:
        if h["income"] <= 1_000_000:
            continue
        assert h["state_tax_change"] > 0, (
            f"household {h['label']}: state_tax_change="
            f"{h['state_tax_change']:.2f} should be positive (7.4-8.4% "
            "top rates exceed the 4.4% flat rate). Baseline/reform may "
            "have been swapped."
        )
        assert h["net_income_change"] < 0, (
            f"household {h['label']}: net_income_change should be "
            "negative for a >$1M earner under Initiative 195."
        )


def test_sign_convention_middle_income_does_not_pay_more(
    households: list[dict],
) -> None:
    """Wage households at or below $100k face 3.7%/4.2% (< 4.4% flat):
    their CO tax cannot rise under Initiative 195."""
    for h in households:
        if not (0 < h["income"] <= 100_000):
            continue
        assert h["state_tax_change"] <= 0.01, (
            f"household {h['label']}: state_tax_change="
            f"{h['state_tax_change']:.2f} should be <= 0 for wages "
            "<= $100k."
        )


def test_state_sweep_matches_expected_shape(households: list[dict]) -> None:
    """Along the sweep, CO tax change must be <= ~0 below $100k of
    wages and positive well above $500k for every profile."""
    for h in households:
        xs = h["chart"]["income_range"]
        state = h["chart"]["state_tax_change"]
        for x, s in zip(xs, state):
            if 0 < x <= 100_000:
                assert s <= 1, (
                    f"{h['label']}: state_tax_change {s:.2f} at "
                    f"income {x} should not be positive"
                )
        top = [s for x, s in zip(xs, state) if x >= 1_200_000]
        assert top and all(s > 0 for s in top), (
            f"{h['label']}: expected positive state tax change at "
            ">= $1.2M sweep incomes"
        )
