"""Modal-based congressional-district pipeline for Colorado Initiative 195.

Calculates district-level impacts for Colorado's 8 congressional
districts (CO-01..CO-08; state FIPS 08) for tax year 2027 using
district-specific calibrated datasets on HuggingFace.

Direction and signs follow scripts/DATA_SCHEMA.md: baseline = current
law (flat 4.4%), reform = Initiative 195 graduated schedule (contrib
flag from 2027); every change is ``reform - baseline``.

Caveat: district files are calibrated independently — district results
do not sum exactly to the statewide totals.

Output: frontend/public/data/congressional_districts.csv

Usage:
    modal run scripts/modal_district_pipeline.py
"""

import os

import modal

# Exact policyengine-us pin — first release containing PR #9431
# (Colorado Initiative 195 graduated income tax contributed reform).
# Mirrored in pyproject.toml, co_tax_calc/reforms.py, and
# scripts/modal_pipeline.py. Keep all four in sync.
POLICYENGINE_US_PIN = "policyengine-us==1.825.0"

# Initiative 195's first tax year; the dashboard covers this single year.
YEAR = 2027

# Colorado: 8 congressional districts, state FIPS 08.
CO_STATE = "CO"
CO_STATE_FIPS = 8
CO_DISTRICTS = list(range(1, 9))

# The single parameter override that activates Initiative 195
# (mirrors co_tax_calc.reforms.REFORM_PARAMS).
REFORM_PARAMS = {
    "gov.contrib.states.co.progressive_income_tax.in_effect": {
        "2027-01-01.2100-12-31": True,
    },
}

app = modal.App("co-initiative-195-district-pipeline")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        POLICYENGINE_US_PIN,
        "numpy>=1.24.0",
        "pandas>=2.0.0",
        "huggingface_hub",
    )
)


def get_co_districts() -> list[str]:
    """Return the Colorado congressional district IDs (CO-01..CO-08)."""
    return [f"{CO_STATE}-{d:02d}" for d in CO_DISTRICTS]


@app.function(
    image=image,
    memory=16384,
    timeout=1800,
    retries=2,
)
def calculate_single_district_impact(district_id: str, year: int = YEAR) -> dict:
    """Calculate the Initiative 195 impact for one Colorado district.

    Uses the district-specific dataset on HuggingFace. Returns average
    and relative household net-income change, winners/losers shares,
    the district CO income-tax revenue impact, and poverty percent
    changes. Impact = reform - baseline.
    """
    import numpy as np
    from policyengine_core.reforms import Reform
    from policyengine_us import Microsimulation

    print(f"Calculating impact for {district_id} TY{year}...")

    dataset_url = (
        f"hf://policyengine/policyengine-us-data/districts/{district_id}.h5"
    )

    reform = Reform.from_dict(REFORM_PARAMS, country_id="us")

    # Baseline = current law (flat tax). Reform = Initiative 195.
    sim_baseline = Microsimulation(dataset=dataset_url)
    sim_reform = Microsimulation(dataset=dataset_url, reform=reform)

    household_weight = np.array(
        sim_baseline.calculate("household_weight", period=year)
    )
    baseline_net_income = np.array(
        sim_baseline.calculate("household_net_income", period=year)
    )
    reform_net_income = np.array(
        sim_reform.calculate("household_net_income", period=year)
    )
    income_change = reform_net_income - baseline_net_income

    # District CO income-tax revenue impact (government-side sign:
    # positive = more revenue) + startup sanity check that the reform
    # actually moved CO tax — a zero delta means the contrib flag did
    # not activate (e.g. a stale pin without PR #9431).
    co_tax_baseline = np.array(
        sim_baseline.calculate("co_income_tax", period=year, map_to="household")
    )
    co_tax_reform = np.array(
        sim_reform.calculate("co_income_tax", period=year, map_to="household")
    )
    state_revenue_impact = float(
        ((co_tax_reform - co_tax_baseline) * household_weight).sum()
    )
    if abs(state_revenue_impact) < 1.0:
        raise RuntimeError(
            f"Sanity check failed for {district_id}: Initiative 195 "
            "reform produced no change in CO income-tax revenue. Check "
            f"that {POLICYENGINE_US_PIN} includes PR #9431."
        )

    total_weight = household_weight.sum()

    if total_weight > 0:
        avg_change = (income_change * household_weight).sum() / total_weight
        avg_baseline = (
            baseline_net_income * household_weight
        ).sum() / total_weight
        rel_change = avg_change / avg_baseline if avg_baseline > 0 else 0.0

        winners_mask = income_change > 1
        losers_mask = income_change < -1
        winners_share = (household_weight * winners_mask).sum() / total_weight
        losers_share = (household_weight * losers_mask).sum() / total_weight
    else:
        avg_change = 0.0
        rel_change = 0.0
        winners_share = 0.0
        losers_share = 0.0

    try:
        spm_unit_weight = np.array(
            sim_baseline.calculate("spm_unit_weight", period=year)
        )
        total_spm_weight = spm_unit_weight.sum()

        if total_spm_weight > 0:
            baseline_in_poverty = np.array(
                sim_baseline.calculate(
                    "spm_unit_is_in_spm_poverty", period=year
                )
            )
            reform_in_poverty = np.array(
                sim_reform.calculate(
                    "spm_unit_is_in_spm_poverty", period=year
                )
            )

            baseline_poverty_rate = (
                baseline_in_poverty * spm_unit_weight
            ).sum() / total_spm_weight
            reform_poverty_rate = (
                reform_in_poverty * spm_unit_weight
            ).sum() / total_spm_weight
            # reform - baseline, relative to baseline (current law).
            poverty_pct_change = (
                (reform_poverty_rate - baseline_poverty_rate)
                / baseline_poverty_rate
                * 100
                if baseline_poverty_rate > 0
                else 0.0
            )

            spm_unit_children = np.array(
                sim_baseline.calculate("spm_unit_count_children", period=year)
            )
            child_weight = spm_unit_weight * spm_unit_children
            total_child_weight = child_weight.sum()

            if total_child_weight > 0:
                baseline_child_poverty_rate = (
                    baseline_in_poverty * child_weight
                ).sum() / total_child_weight
                reform_child_poverty_rate = (
                    reform_in_poverty * child_weight
                ).sum() / total_child_weight
                child_poverty_pct_change = (
                    (reform_child_poverty_rate - baseline_child_poverty_rate)
                    / baseline_child_poverty_rate
                    * 100
                    if baseline_child_poverty_rate > 0
                    else 0.0
                )
            else:
                child_poverty_pct_change = 0.0
        else:
            poverty_pct_change = 0.0
            child_poverty_pct_change = 0.0
    except Exception as poverty_err:
        print(
            f"  Warning: Poverty calculation failed for {district_id}: "
            f"{poverty_err}"
        )
        poverty_pct_change = 0.0
        child_poverty_pct_change = 0.0

    result = {
        "district": district_id,
        "average_household_income_change": round(float(avg_change), 2),
        "relative_household_income_change": round(float(rel_change), 6),
        "winners_share": round(float(winners_share), 4),
        "losers_share": round(float(losers_share), 4),
        "affected_share": round(float(winners_share + losers_share), 4),
        "state_revenue_impact": round(state_revenue_impact, 2),
        "poverty_pct_change": round(float(poverty_pct_change), 2),
        "child_poverty_pct_change": round(float(child_poverty_pct_change), 2),
        "state": CO_STATE,
        "year": year,
    }

    print(
        f"  {district_id} TY{year}: avg=${avg_change:.2f}, "
        f"winners={winners_share:.1%}, losers={losers_share:.1%}, "
        f"revenue=${state_revenue_impact:,.0f}"
    )
    return result


@app.local_entrypoint()
def main():
    """Run the Colorado district analysis on Modal and save the CSV."""
    import pandas as pd

    output_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "frontend",
        "public",
        "data",
    )
    os.makedirs(output_dir, exist_ok=True)

    districts = get_co_districts()

    print("Running Colorado Initiative 195 district analysis on Modal...")
    print(f"Pin: {POLICYENGINE_US_PIN}")
    print(f"Year: {YEAR}")
    print(f"State: {CO_STATE} (FIPS {CO_STATE_FIPS:02d})")
    print(f"Districts: {districts}")
    print(f"Output directory: {output_dir}")

    results = list(calculate_single_district_impact.map(districts))
    rows = [r for r in results if r is not None]

    if len(rows) < len(districts):
        missing = {d for d in districts} - {r["district"] for r in rows}
        raise SystemExit(
            f"ERROR: {len(districts) - len(rows)} districts failed to "
            f"calculate: {sorted(missing)}"
        )

    df = (
        pd.DataFrame(rows)
        .sort_values(["year", "state", "district"])
        .reset_index(drop=True)
    )
    filepath = os.path.join(output_dir, "congressional_districts.csv")
    df.to_csv(filepath, index=False)
    print(f"\nSaved {len(df)} rows to: {filepath}")

    print("\nSummary:")
    print(
        f"  avg=${df['average_household_income_change'].mean():,.2f}  "
        f"(min ${df['average_household_income_change'].min():,.2f}, "
        f"max ${df['average_household_income_change'].max():,.2f})"
    )
