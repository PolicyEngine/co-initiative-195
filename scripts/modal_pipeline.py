"""Modal data pipeline for Colorado Initiative 195 (detach-safe).

Runs ONE national baseline and ONE national reform Microsimulation for
tax year 2027 on the Populace build P ACS local-area dataset and
produces BOTH the statewide CSVs and the congressional-district CSV
from that single pass.

DETACH-SAFE DESIGN: the remote function writes every output CSV plus a
manifest.json into a modal.Volume ("co-initiative-195-results") and
commits it, so results survive even if the local `modal run` driver
process dies mid-run (which loses in-memory return values). Kick off
with --detach (fire-and-forget), then fetch the committed CSVs in
seconds with the separate lightweight entrypoint:

    # 1. Fire and forget -- remote job survives local death
    modal run --detach scripts/modal_pipeline.py::kickoff

    # 2. Later (seconds): verify the manifest and download the CSVs
    modal run scripts/modal_pipeline.py::fetch

    # (equivalent manual fetch)
    modal volume get co-initiative-195-results / frontend/public/data/

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

Outputs (Volume root -> frontend/public/data/): metrics.csv,
distributional_impact.csv, winners_losers.csv, income_brackets.csv,
congressional_districts.csv, plus manifest.json (not copied to the
frontend).
"""

import json
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

# Results volume: the remote fn writes + commits here so a dead local
# driver cannot lose the run.
RESULTS_VOLUME_NAME = "co-initiative-195-results"
RESULTS_DIR = "/results"
MANIFEST_NAME = "manifest.json"
CSV_FILES = [
    "metrics.csv",
    "distributional_impact.csv",
    "winners_losers.csv",
    "income_brackets.csv",
    "congressional_districts.csv",
]

app = modal.App("co-initiative-195-pipeline")

results_volume = modal.Volume.from_name(
    RESULTS_VOLUME_NAME, create_if_missing=True
)

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


def _build_csv_rows(result: dict, year: int) -> dict:
    """Turn calculate_impacts() output into {filename: rows} per the
    DATA_SCHEMA.md contract. Pure function (also unit-testable)."""
    statewide = result["statewide"]

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

    district_rows = sorted(result["districts"], key=lambda r: r["district"])

    return {
        "metrics.csv": metrics_rows,
        "distributional_impact.csv": distributional_rows,
        "winners_losers.csv": winners_losers_rows,
        "income_brackets.csv": income_bracket_rows,
        "congressional_districts.csv": district_rows,
    }


@app.function(
    image=image,
    memory=65536,  # 64GB: two full national sims (~1.6M households)
    timeout=3 * 3600,
    retries=1,
    volumes={RESULTS_DIR: results_volume},
)
def compute(year: int) -> dict:
    """Run the national pass and persist all CSVs + manifest to the
    results Volume (committed), so nothing depends on the local driver
    staying alive."""
    from datetime import datetime, timezone

    import pandas as pd

    from co_tax_calc.microsimulation import (
        POPULACE_FILENAME,
        POPULACE_REPO,
        POPULACE_REVISION,
        calculate_impacts,
    )

    print(f"Starting Colorado Initiative 195 calculation for TY{year}...")
    print(f"Dataset: {POPULACE_FILENAME} @ {POPULACE_REVISION}")
    result = calculate_impacts(year=year)

    csvs = _build_csv_rows(result, year)
    for filename, rows in csvs.items():
        filepath = os.path.join(RESULTS_DIR, filename)
        pd.DataFrame(rows).to_csv(filepath, index=False)
        print(f"  Wrote {filepath}")

    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "year": year,
        "pin": POLICYENGINE_US_PIN,
        "dataset_repo": POPULACE_REPO,
        "dataset_revision": POPULACE_REVISION,
        "dataset_filename": POPULACE_FILENAME,
        "files": list(csvs.keys()),
        "state_tax_revenue_impact": result["statewide"]["budget"][
            "state_tax_revenue_impact"
        ],
        "districts": len(result["districts"]),
    }
    with open(os.path.join(RESULTS_DIR, MANIFEST_NAME), "w") as fh:
        json.dump(manifest, fh, indent=2)

    results_volume.commit()
    print(
        "COMPLETE: results committed to volume "
        f"'{RESULTS_VOLUME_NAME}'. CO revenue impact: "
        f"${manifest['state_tax_revenue_impact']:,.0f}; "
        f"{manifest['districts']} districts. Fetch with: "
        "modal run scripts/modal_pipeline.py::fetch"
    )
    return manifest


@app.local_entrypoint()
def kickoff():
    """Fire-and-forget kickoff. Run with:

        modal run --detach scripts/modal_pipeline.py::kickoff

    The remote job keeps running (and commits its results to the
    Volume) even if this local process dies immediately after spawn.
    """
    print(f"Kicking off Colorado Initiative 195 pipeline for TY{YEAR}...")
    print(f"Pin: {POLICYENGINE_US_PIN}")
    handle = compute.spawn(YEAR)
    print(f"Spawned remote function call: {handle.object_id}")
    print(
        "Results will be committed to volume "
        f"'{RESULTS_VOLUME_NAME}' when done. Fetch with: "
        "modal run scripts/modal_pipeline.py::fetch"
    )


@app.local_entrypoint()
def fetch():
    """Lightweight fetch: verify the manifest, then download the CSVs
    from the results Volume into frontend/public/data/ (seconds).

        modal run scripts/modal_pipeline.py::fetch

    Equivalent manual command:
        modal volume get co-initiative-195-results / frontend/public/data/
    """
    output_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "frontend",
        "public",
        "data",
    )
    os.makedirs(output_dir, exist_ok=True)

    def read_volume_file(path: str) -> bytes:
        return b"".join(results_volume.read_file(path))

    try:
        manifest = json.loads(read_volume_file(MANIFEST_NAME))
    except Exception as err:
        raise SystemExit(
            f"No readable {MANIFEST_NAME} in volume "
            f"'{RESULTS_VOLUME_NAME}' ({err}). The compute job may "
            "still be running -- check `modal app list` / the app logs."
        )

    print(f"Manifest: generated {manifest['generated_at_utc']}")
    print(f"  pin: {manifest['pin']}")
    print(f"  dataset revision: {manifest['dataset_revision']}")

    if manifest["pin"] != POLICYENGINE_US_PIN:
        raise SystemExit(
            f"Manifest pin {manifest['pin']} does not match local "
            f"{POLICYENGINE_US_PIN} -- results are from a different "
            "build. Re-run the pipeline."
        )
    missing = [f for f in CSV_FILES if f not in manifest.get("files", [])]
    if missing:
        raise SystemExit(
            f"Manifest is missing expected files: {missing}. "
            "The run may be incomplete."
        )

    for filename in manifest["files"]:
        content = read_volume_file(filename)
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "wb") as fh:
            fh.write(content)
        print(f"Saved: {filepath}")

    print(f"\nDone! All data saved to {output_dir}/")
