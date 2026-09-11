"""Pre-compute representative Colorado households for the household tab.

For each profile, runs a current-law (flat 4.4%) simulation and an
Initiative 195 (graduated schedule) simulation at the profile's income
point, plus an employment-income sweep from $0 to $1,300,000 so the
chart shows all six brackets -- including the 8.4% bracket above $1M.

Direction and signs follow scripts/DATA_SCHEMA.md:

- ``net_income_change`` = reform - baseline household net income
  (negative = the household pays more tax under Initiative 195).
- ``state_tax_change`` / ``federal_tax_change`` are tax-side:
  reform - baseline tax (positive = pays more tax).

There is no per-provision attribution: Initiative 195 is a single
provision (one contrib flag), so the GA template's ``provisions`` /
``provisions_chart`` keys are intentionally gone.

Runs locally (no Modal):
    .venv/Scripts/python.exe scripts/compute_example_households.py
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from policyengine_us import Simulation  # noqa: E402

from co_tax_calc.reforms import (  # noqa: E402
    POLICYENGINE_US_PIN,
    create_co_reform,
)

YEAR = 2027
OUTPUT_PATH = (
    REPO_ROOT / "frontend" / "public" / "data" / "example_households.json"
)

# Employment-income sweep: $0..$1,300,000 in $10k steps. The step lands
# exactly on every Initiative 195 bracket threshold (25k / 100k / 500k /
# 750k / 1M).
SWEEP_MAX = 1_300_000
SWEEP_COUNT = 131

# Representative Colorado household profiles. The last profile earns
# more than $1,000,000 so the top 8.4% bracket is exercised.
PROFILES = [
    {
        "label": "Single filer, $45k wages",
        "income": 45_000,
        "age_head": 28,
        "married": False,
        "dependents": [],
    },
    {
        "label": "Married couple, $95k, 2 kids",
        "income": 95_000,
        "age_head": 40,
        "married": True,
        "dependents": [6, 9],
    },
    {
        "label": "Retired couple, $60k pension + Social Security",
        "income": 0,
        "age_head": 68,
        "age_spouse": 67,
        "married": True,
        "dependents": [],
        "taxable_pension_income": 60_000,
        "social_security_retirement": 30_000,
    },
    {
        "label": "Married couple, $1.2M wages, 2 kids",
        "income": 1_200_000,
        "age_head": 50,
        "married": True,
        "dependents": [13, 16],
    },
]


def build_household(profile: dict, with_axes: bool = False) -> dict:
    """Build a PolicyEngine household situation for the given profile.

    If ``with_axes`` is True, sweeps employment_income from $0 to
    $1,300,000 so we can pre-compute the full net-income chart.
    """
    year = str(YEAR)
    income_for_point = None if with_axes else profile["income"]
    you_attrs: dict = {
        "age": {year: profile["age_head"]},
        "employment_income": {year: income_for_point},
    }
    for var in ("taxable_pension_income", "social_security_retirement"):
        if var in profile:
            you_attrs[var] = {year: profile[var]}
    people: dict = {"you": you_attrs}
    members = ["you"]
    marital_units: dict = {"your marital unit": {"members": ["you"]}}

    if profile["married"]:
        people["your partner"] = {
            "age": {year: profile.get("age_spouse", 35)}
        }
        members.append("your partner")
        marital_units["your marital unit"]["members"].append("your partner")

    for i, age in enumerate(profile["dependents"]):
        cid = (
            "your first dependent"
            if i == 0
            else "your second dependent"
            if i == 1
            else f"dependent_{i + 1}"
        )
        people[cid] = {"age": {year: age}}
        members.append(cid)
        marital_units[f"{cid}'s marital unit"] = {"members": [cid]}

    situation: dict = {
        "people": people,
        "families": {"your family": {"members": members}},
        "marital_units": marital_units,
        "spm_units": {"your household": {"members": members}},
        "tax_units": {
            "your tax unit": {
                "members": members,
                "adjusted_gross_income": {year: None},
                "income_tax": {year: None},
                "co_income_tax": {year: None},
            }
        },
        "households": {
            "your household": {
                "members": members,
                "state_code": {year: "CO"},
                "household_net_income": {year: None},
            }
        },
    }

    if with_axes:
        situation["axes"] = [
            [
                {
                    "name": "employment_income",
                    "min": 0,
                    "max": SWEEP_MAX,
                    "count": SWEEP_COUNT,
                    "period": year,
                    "target": "person",
                }
            ]
        ]
    return situation


def make_sim(situation: dict, reformed: bool) -> Simulation:
    """Build a baseline (current-law) or Initiative 195 Simulation."""
    if reformed:
        return Simulation(situation=situation, reform=create_co_reform())
    return Simulation(situation=situation)


def extract(sim: Simulation) -> dict:
    """Pull the single-point values (no axes) from a Simulation."""
    yr = str(YEAR)
    return {
        "household_net_income": float(
            sim.calculate("household_net_income", yr, map_to="household")[0]
        ),
        "co_income_tax": float(
            sim.calculate("co_income_tax", yr, map_to="tax_unit")[0]
        ),
        "income_tax": float(
            sim.calculate("income_tax", yr, map_to="tax_unit")[0]
        ),
    }


def sweep_arrays(sim: Simulation) -> dict:
    """Pull the sweep arrays from a Simulation built with an axis.

    All arrays are aggregated to the household level so they share the
    axis length. ``income_range`` sums employment_income over household
    members, which equals the head's wages since only ``you`` earns.
    """
    yr = str(YEAR)
    return {
        "income_range": sim.calculate(
            "employment_income", yr, map_to="household"
        ).tolist(),
        "net_income": sim.calculate(
            "household_net_income", yr, map_to="household"
        ).tolist(),
        "state_tax": sim.calculate(
            "co_income_tax", yr, map_to="household"
        ).tolist(),
        "federal_tax": sim.calculate(
            "income_tax", yr, map_to="household"
        ).tolist(),
    }


def _diff(reform: list[float], baseline: list[float]) -> list[float]:
    """Element-wise reform - baseline."""
    return [r - b for r, b in zip(reform, baseline)]


def compute_profile(profile: dict) -> dict:
    """Run baseline and Initiative 195 sims at the profile's income
    point and across the income sweep."""
    point_situation = build_household(profile, with_axes=False)
    sweep_situation = build_household(profile, with_axes=True)

    base_pt = extract(make_sim(point_situation, reformed=False))
    reform_pt = extract(make_sim(point_situation, reformed=True))
    base_sweep = sweep_arrays(make_sim(sweep_situation, reformed=False))
    reform_sweep = sweep_arrays(make_sim(sweep_situation, reformed=True))

    return {
        **profile,
        "baseline": base_pt,
        "reform": reform_pt,
        # Household-side: negative = pays more tax under the initiative.
        "net_income_change": (
            reform_pt["household_net_income"]
            - base_pt["household_net_income"]
        ),
        # Tax-side: positive = pays more tax under the initiative.
        "state_tax_change": (
            reform_pt["co_income_tax"] - base_pt["co_income_tax"]
        ),
        "federal_tax_change": (
            reform_pt["income_tax"] - base_pt["income_tax"]
        ),
        "chart": {
            "income_range": base_sweep["income_range"],
            "net_income_change": _diff(
                reform_sweep["net_income"], base_sweep["net_income"]
            ),
            "state_tax_change": _diff(
                reform_sweep["state_tax"], base_sweep["state_tax"]
            ),
            "federal_tax_change": _diff(
                reform_sweep["federal_tax"], base_sweep["federal_tax"]
            ),
        },
    }


def _validate_sign_convention(rows: list[dict]) -> None:
    """Fail loud if the forward sign convention got flipped.

    Initiative 195 keeps 4.4% between $100k and $500k, cuts below
    $100k (3.7% / 4.2%), and raises above $500k (7.4% / 7.9% / 8.4%).
    So a >$1M household must show a POSITIVE state_tax_change (pays
    more), and a modest-income wage household must show a non-positive
    one. Also guard against an inert reform (all-zero deltas).
    """
    if all(
        abs(v) < 0.01
        for row in rows
        for v in row["chart"]["state_tax_change"]
    ):
        raise SystemExit(
            "Sanity check failed: the Initiative 195 reform produced no "
            "CO tax change anywhere in the sweep. Check that "
            f"{POLICYENGINE_US_PIN} includes PR #9431."
        )
    for row in rows:
        if row["income"] > 1_000_000:
            if row["state_tax_change"] <= 0:
                raise SystemExit(
                    f"Sign-convention check failed for {row['label']}: "
                    f"state_tax_change={row['state_tax_change']:.2f} but a "
                    ">$1M household must pay MORE CO tax under Initiative "
                    "195 (positive tax-side change). Did baseline and "
                    "reform get swapped?"
                )
        elif 0 < row["income"] <= 100_000:
            if row["state_tax_change"] > 0:
                raise SystemExit(
                    f"Sign-convention check failed for {row['label']}: "
                    f"state_tax_change={row['state_tax_change']:.2f} but a "
                    "<=100k wage household cannot pay more CO tax under "
                    "Initiative 195 (3.7%/4.2% below the 4.4% flat rate)."
                )


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for profile in PROFILES:
        print(f"  Computing: {profile['label']}...")
        rows.append(compute_profile(profile))

    _validate_sign_convention(rows)

    payload = {
        "year": YEAR,
        "pin": POLICYENGINE_US_PIN,
        "households": rows,
    }
    with OUTPUT_PATH.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    print(f"Saved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
