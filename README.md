# Colorado Initiative 195 (Amendment 87) dashboard

Models the impact of Colorado Initiative 195 — ballot designation
"Amendment 87" on the November 2026 ballot — which would replace Colorado's
4.4% flat income tax with six graduated brackets on Colorado taxable income,
uniform across filing statuses, effective tax year 2027:

| Colorado taxable income | Rate |
|---|---|
| $0 – $25,000 | 3.7% |
| $25,000 – $100,000 | 4.2% |
| $100,000 – $500,000 | 4.4% |
| $500,000 – $750,000 | 7.4% |
| $750,000 – $1,000,000 | 7.9% |
| Over $1,000,000 | 8.4% |

Official text: [Initiative 195 final filing](https://www.sos.state.co.us/pubs/elections/Initiatives/titleBoard/filings/2025-2026/195Final.pdf).

## How it is modeled

- **Reform (forward direction)**: baseline = current law (flat 4.4%); reform
  sets the contributed parameter
  `gov.contrib.states.co.progressive_income_tax.in_effect` to true from
  2027-01-01 (policyengine-us PR #9431). Everywhere in this repository,
  `impact = reform − baseline`.
- **Pin**: `policyengine-us==1.825.0` — the first release containing PR
  #9431. The pin lives in four synchronized places: `pyproject.toml`,
  `co_tax_calc/reforms.py`, `scripts/modal_pipeline.py`,
  `scripts/modal_district_pipeline.py`. Each Modal pipeline raises at startup
  if the reform produces no CO income-tax revenue delta (stale-pin guard).
- **Year**: tax year 2027 only.
- **Python package**: `co_tax_calc/` (reform definition, household situation
  builder, statewide microsimulation).
- **Frontend**: `frontend/` (Next.js / Tailwind).

## Data pipelines

Output schemas are documented in [`scripts/DATA_SCHEMA.md`](scripts/DATA_SCHEMA.md)
(the contract the frontend is coded against).

```bash
# One-time setup
uv venv --python 3.13 .venv
uv pip install -p .venv/Scripts/python.exe -e ".[dev]"

# Statewide CSVs (Modal; hf://policyengine/policyengine-us-data/states/CO.h5)
modal run scripts/modal_pipeline.py

# CO-01..CO-08 district CSV (Modal; districts/CO-0N.h5, FIPS 08)
modal run scripts/modal_district_pipeline.py

# Example household profiles + income sweeps (local, no Modal)
.venv/Scripts/python.exe scripts/compute_example_households.py

# Python tests
.venv/Scripts/python.exe -m pytest tests
```

All outputs land in `frontend/public/data/` and are committed. The map
geojson (`frontend/public/data/geojson/`) is national 119th-Congress data and
already includes Colorado's 8 districts (`DISTRICT_ID` CO-01..CO-08).

## Known modeling limitations

- The initiative's (1.8)(b) home-sale carve-out (section 121-excess gains
  taxed at a flat 4.4%) is not modeled: this understates tax for filers at or
  below $100,000 with such gains, has no effect between $100,000 and
  $500,000, and overstates tax above $500,000.
- The corporate schedule (Section 4) and TABOR / Colorado's Future Fund
  accounting (Section 5) are outside the household model's scope.
- District files are calibrated independently; district results do not sum
  exactly to the statewide totals.

## Deploy

Vercel project `co-initiative-195`, multi-zone basePath
`/us/co-initiative-195` (`vercel deploy --prod --scope policy-engine`, plus
an appZoneRoutes entry).

Live: TBD.
