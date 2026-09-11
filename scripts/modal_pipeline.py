"""Modal data pipeline for Colorado Initiative 195 (single merged app).

Runs ONE national baseline and ONE national reform Microsimulation for
tax year 2027 on the Populace build P ACS local-area dataset and
produces BOTH the statewide CSVs and the congressional-district CSV
from that single pass (the two-app statewide/district split from the
GA template is gone -- no reason to run a 1.6M-household simulation
twice).

Dataset (single national file, ~1.6M households, PUMA-assigned
CD-119 / county / state geography):
    repo_id  policyengine/populace-us (HF dataset repo)
    revision populace-us-2024-buildp-acs-local-592ae5d6-20260819T020303Z
    filename populace_us_2024_acs_local.h5
Loaded FUTA-template style: hf_hub_download(...) then
Microsimulation(dataset=<local path>). Colorado = state_fips 8;
districts = congressional_district_geoid 801..808 (SSDD encoding,
verified empirically against the h5).

Direction and signs follow scripts/DATA_SCHEMA.md: baseline = current
law (flat 4.4%), reform = Initiative 195 (contrib flag from 2027);
every change is reform - baseline. The compute delegates to
co_tax_calc.microsimulation.calculate_impacts, which raises at startup
if the reform moves no CO income-tax revenue (stale-pin guard) or if
the geography columns stop matching expectations.

Outputs (frontend/public/data/): metrics.csv, distributional_impact.csv,
winners_losers.csv, income_brackets.csv, congressional_districts.csv.

Usage:
    modal run scripts/modal_pipeline.py
"""

import os

import modal

# Exact policyengine-us pin -- first release containing PR #9431
# (Colorado Initiative 195 graduated income tax contributed reform).
# Mirrored in pyproject.toml and co_tax_calc/reforms.py. Keep all
# three in sync. Do NOT switch to the `policyengine` wrapper package:
# its latest bundle pins policyengine-us 1.764.6, which predates the
# contrib parameter.
POLICYENGINE_US_PIN = "policyengine-us==1.825.0"

# Initiative 195's first tax year; the dashboard covers this single year.
YEAR = 2027

app = modal.App("co-initiative-195-pipeline")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        POLICYENGINE_US_PIN,
        "numpy>=1.24.0",
        "pandas>=2.0.0",
        "tables>=3.8.0",  # pandas-HDF reader for the populace h5
        "huggingface_hub",
    )
    # Ship the local calculation module so the aggregate math (and its
    # sanity checks) lives in exactly one place.
    .add_local_python_source("co_tax_calc")
)


@app.function(
    image=image,
    memory=65536,  # 64GB: two full national sims (~1.6M households)
    timeout=3 * 3600,
    retries=1,
)
def calculate_all(year: int) -> dict:
    """Run the national pass on Modal; return statewide + districts."""
    from co_tax_calc.microsimulation import (
        POPULACE_FILENAME,
        POPULACE_REVISION,
        calculate_impacts,
    )

    print(f"Starting Colorado Initiative 195 calculation for TY{year}...")
    print(f"Dataset: {POPULACE_FILENAME} @ {POPULACE_REVISION}")
    result = calculate_impacts(year=year)
    print(
        "  Done. CO revenue impact: "
        f"${result['statewide']['budget']['state_tax_revenue_impact']:,.0f}; "
        f"{len(result['districts'])} districts."
    )
    return result


@app.local_entrypoint()
def main():
    """Run the pipeline on Modal and save all CSVs locally."""
    import pandas as pd

    output_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "frontend",
        "public",
        "data",
    )
    os.makedirs(output_dir, exist_ok=True)

    print(f"Running Colorado Initiative 195 pipeline for TY{YEAR} on Modal...")
    print(f"Pin: {POLICYENGINE_US_PIN}")
    print(f"Output directory: {output_dir}")

    result = calculate_all.remote(YEAR)
    statewide = result["statewide"]
    districts = result["districts"]
    year = YEAR

    # distributional_impact.csv
    distributional_rows = [
        {
            "year": year,
            "decile": decile,
            "average_change": round(avg, 2),
            "relative_change": round(
                statewide["decile"]["relative"][decile], 6
            ),
        }
        for decile, avg in statewide["decile"]["average"].items()
    ]

    # metrics.csv
    metrics = [
        ("budgetary_impact", statewide["budget"]["budgetary_impact"]),
        ("federal_tax_revenue_impact", statewide["budget"]["federal_tax_revenue_impact"]),
        ("state_tax_revenue_impact", statewide["budget"]["state_tax_revenue_impact"]),
        ("tax_revenue_impact", statewide["budget"]["tax_revenue_impact"]),
        ("households", statewide["budget"]["households"]),
        ("avg_household_net_income_change", statewide["avg_household_net_income_change"]),
        ("total_cost", statewide["total_cost"]),
        ("beneficiaries", statewide["beneficiaries"]),
        ("avg_benefit", statewide["avg_benefit"]),
        ("winners", statewide["winners"]),
        ("losers", statewide["losers"]),
        ("winners_rate", statewide["winners_rate"]),
        ("losers_rate", statewide["losers_rate"]),
        ("poverty_baseline_rate", statewide["poverty_baseline_rate"]),
        ("poverty_reform_rate", statewide["poverty_reform_rate"]),
        ("poverty_rate_change", statewide["poverty_rate_change"]),
        ("poverty_percent_change", statewide["poverty_percent_change"]),
        ("child_poverty_baseline_rate", statewide["child_poverty_baseline_rate"]),
        ("child_poverty_reform_rate", statewide["child_poverty_reform_rate"]),
        ("child_poverty_rate_change", statewide["child_poverty_rate_change"]),
        ("child_poverty_percent_change", statewide["child_poverty_percent_change"]),
        ("deep_poverty_baseline_rate", statewide["deep_poverty_baseline_rate"]),
        ("deep_poverty_reform_rate", statewide["deep_poverty_reform_rate"]),
        ("deep_poverty_rate_change", statewide["deep_poverty_rate_change"]),
        ("deep_poverty_percent_change", statewide["deep_poverty_percent_change"]),
        ("deep_child_poverty_baseline_rate", statewide["deep_child_poverty_baseline_rate"]),
        ("deep_child_poverty_reform_rate", statewide["deep_child_poverty_reform_rate"]),
        ("deep_child_poverty_rate_change", statewide["deep_child_poverty_rate_change"]),
        ("deep_child_poverty_percent_change", statewide["deep_child_poverty_percent_change"]),
    ]
    metrics_rows = [
        {"year": year, "metric": metric, "value": value}
        for metric, value in metrics
    ]

    # winners_losers.csv
    intra = statewide["intra_decile"]
    winners_losers_rows = [
        {
            "year": year,
            "decile": "All",
            "gain_more_5pct": intra["all"]["Gain more than 5%"],
            "gain_less_5pct": intra["all"]["Gain less than 5%"],
            "no_change": intra["all"]["No change"],
            "lose_less_5pct": intra["all"]["Lose less than 5%"],
            "lose_more_5pct": intra["all"]["Lose more than 5%"],
        }
    ]
    for i in range(10):
        winners_losers_rows.append({
            "year": year,
            "decile": str(i + 1),
            "gain_more_5pct": intra["deciles"]["Gain more than 5%"][i],
            "gain_less_5pct": intra["deciles"]["Gain less than 5%"][i],
            "no_change": intra["deciles"]["No change"][i],
            "lose_less_5pct": intra["deciles"]["Lose less than 5%"][i],
            "lose_more_5pct": intra["deciles"]["Lose more than 5%"][i],
        })

    # income_brackets.csv
    income_bracket_rows = [
        {
            "year": year,
            "bracket": b["bracket"],
            "households": b["households"],
            "beneficiaries": b["beneficiaries"],
            "total_cost": b["total_cost"],
            "avg_benefit": b["avg_benefit"],
        }
        for b in statewide["by_income_bracket"]
    ]

    # congressional_districts.csv
    district_rows = sorted(districts, key=lambda r: r["district"])

    for rows, filename in [
        (distributional_rows, "distributional_impact.csv"),
        (metrics_rows, "metrics.csv"),
        (winners_losers_rows, "winners_losers.csv"),
        (income_bracket_rows, "income_brackets.csv"),
        (district_rows, "congressional_districts.csv"),
    ]:
        filepath = os.path.join(output_dir, filename)
        pd.DataFrame(rows).to_csv(filepath, index=False)
        print(f"Saved: {filepath}")

    print(f"\nDone! All data saved to {output_dir}/")
