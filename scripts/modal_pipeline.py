"""Modal-based statewide data pipeline for Colorado Initiative 195.

Runs the forward Initiative 195 reform (contrib flag
``gov.contrib.states.co.progressive_income_tax.in_effect`` = true from
2027) against the Colorado state dataset on Modal for tax year 2027.

Direction and signs follow scripts/DATA_SCHEMA.md: baseline = current
law (flat 4.4%), reform = Initiative 195 graduated schedule, every
change is ``reform - baseline``. Revenue impacts are government-side
(positive = more revenue); household amounts are household-side
(negative = pays more tax).

Outputs (frontend/public/data/): metrics.csv,
distributional_impact.csv, winners_losers.csv, income_brackets.csv.

Usage:
    modal run scripts/modal_pipeline.py
"""

import os

import modal

# Exact policyengine-us pin — first release containing PR #9431
# (Colorado Initiative 195 graduated income tax contributed reform).
# Mirrored in pyproject.toml, co_tax_calc/reforms.py, and
# scripts/modal_district_pipeline.py. Keep all four in sync.
POLICYENGINE_US_PIN = "policyengine-us==1.825.0"

# Initiative 195's first tax year; the dashboard covers this single year.
YEAR = 2027

# Colorado state dataset on HuggingFace.
CO_DATASET = "hf://policyengine/policyengine-us-data/states/CO.h5"

app = modal.App("co-initiative-195-pipeline")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        POLICYENGINE_US_PIN,
        "numpy>=1.24.0",
        "pandas>=2.0.0",
        "huggingface_hub",
    )
    # Ship the local calculation module so the aggregate math (and its
    # startup sanity check) lives in exactly one place.
    .add_local_python_source("co_tax_calc")
)


@app.function(
    image=image,
    memory=16384,  # 16GB is plenty for a single-state dataset
    timeout=1800,
    retries=1,
)
def calculate_statewide(year: int) -> dict:
    """Calculate the statewide Initiative 195 impact on Modal.

    Delegates to ``co_tax_calc.microsimulation.calculate_aggregate_impact``,
    which raises if the reform produces no CO income-tax revenue delta
    (guards against a pin that lacks PR #9431).
    """
    from co_tax_calc.microsimulation import calculate_aggregate_impact

    print(f"Starting statewide calculation for TY{year}...")
    result = calculate_aggregate_impact(year=year)
    result["year"] = year
    print(
        f"  TY{year} complete. CO revenue impact: "
        f"${result['budget']['state_tax_revenue_impact']:,.0f}"
    )
    return result


@app.local_entrypoint()
def main():
    """Run the statewide pipeline on Modal and save CSVs locally."""
    import pandas as pd

    output_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "frontend",
        "public",
        "data",
    )
    os.makedirs(output_dir, exist_ok=True)

    print(f"Running Colorado Initiative 195 microsimulation for TY{YEAR} on Modal...")
    print(f"Pin: {POLICYENGINE_US_PIN}")
    print(f"Dataset: {CO_DATASET}")
    print(f"Output directory: {output_dir}")

    result = calculate_statewide.remote(YEAR)
    year = result["year"]

    # distributional_impact.csv
    distributional_rows = [
        {
            "year": year,
            "decile": decile,
            "average_change": round(avg, 2),
            "relative_change": round(result["decile"]["relative"][decile], 6),
        }
        for decile, avg in result["decile"]["average"].items()
    ]

    # metrics.csv
    metrics = [
        ("budgetary_impact", result["budget"]["budgetary_impact"]),
        ("federal_tax_revenue_impact", result["budget"]["federal_tax_revenue_impact"]),
        ("state_tax_revenue_impact", result["budget"]["state_tax_revenue_impact"]),
        ("tax_revenue_impact", result["budget"]["tax_revenue_impact"]),
        ("households", result["budget"]["households"]),
        ("avg_household_net_income_change", result["avg_household_net_income_change"]),
        ("total_cost", result["total_cost"]),
        ("beneficiaries", result["beneficiaries"]),
        ("avg_benefit", result["avg_benefit"]),
        ("winners", result["winners"]),
        ("losers", result["losers"]),
        ("winners_rate", result["winners_rate"]),
        ("losers_rate", result["losers_rate"]),
        ("poverty_baseline_rate", result["poverty_baseline_rate"]),
        ("poverty_reform_rate", result["poverty_reform_rate"]),
        ("poverty_rate_change", result["poverty_rate_change"]),
        ("poverty_percent_change", result["poverty_percent_change"]),
        ("child_poverty_baseline_rate", result["child_poverty_baseline_rate"]),
        ("child_poverty_reform_rate", result["child_poverty_reform_rate"]),
        ("child_poverty_rate_change", result["child_poverty_rate_change"]),
        ("child_poverty_percent_change", result["child_poverty_percent_change"]),
        ("deep_poverty_baseline_rate", result["deep_poverty_baseline_rate"]),
        ("deep_poverty_reform_rate", result["deep_poverty_reform_rate"]),
        ("deep_poverty_rate_change", result["deep_poverty_rate_change"]),
        ("deep_poverty_percent_change", result["deep_poverty_percent_change"]),
        ("deep_child_poverty_baseline_rate", result["deep_child_poverty_baseline_rate"]),
        ("deep_child_poverty_reform_rate", result["deep_child_poverty_reform_rate"]),
        ("deep_child_poverty_rate_change", result["deep_child_poverty_rate_change"]),
        ("deep_child_poverty_percent_change", result["deep_child_poverty_percent_change"]),
    ]
    metrics_rows = [
        {"year": year, "metric": metric, "value": value}
        for metric, value in metrics
    ]

    # winners_losers.csv
    intra = result["intra_decile"]
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
        for b in result["by_income_bracket"]
    ]

    for rows, filename in [
        (distributional_rows, "distributional_impact.csv"),
        (metrics_rows, "metrics.csv"),
        (winners_losers_rows, "winners_losers.csv"),
        (income_bracket_rows, "income_brackets.csv"),
    ]:
        filepath = os.path.join(output_dir, filename)
        pd.DataFrame(rows).to_csv(filepath, index=False)
        print(f"Saved: {filepath}")

    print(f"\nDone! All data saved to {output_dir}/")
