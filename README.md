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
  #9431. The pin lives in three synchronized places: `pyproject.toml`,
  `co_tax_calc/reforms.py`, `scripts/modal_pipeline.py`. The pipeline raises
  at startup if the reform produces no CO income-tax revenue delta
  (stale-pin guard). Do not substitute the `policyengine` wrapper package —
  its latest bundle pins policyengine-us 1.764.6, which predates the contrib
  parameter.
- **Dataset**: Populace build P ACS local-area national file (~1.6M
  households, PUMA-assigned CD-119 / county / state geography) from the HF
  dataset repo `policyengine/populace-us`, revision
  `populace-us-2024-buildp-acs-local-592ae5d6-20260819T020303Z`, file
  `populace_us_2024_acs_local.h5`, loaded via `hf_hub_download` then
  `Microsimulation(dataset=<path>)`. Colorado = `state_fips` 8; districts =
  `congressional_district_geoid` 801..808 (SSDD encoding).
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

# ALL five CSVs — statewide + congressional districts — in one Modal job
# (single national baseline + reform pass on the build P acs-local file).
# Detach-safe: the remote function writes + commits every CSV plus a
# manifest.json to the Modal Volume "co-initiative-195-results", so the
# run survives local driver death.
modal run --detach scripts/modal_pipeline.py::kickoff

# After the job completes (check `modal app list` / the app logs), fetch
# the CSVs from the Volume into frontend/public/data/ (seconds; verifies
# the manifest's pin and file list first)
modal run scripts/modal_pipeline.py::fetch
# equivalent manual fetch:
#   modal volume get co-initiative-195-results / frontend/public/data/

# Example household profiles + income sweeps (local, no Modal)
.venv/Scripts/python.exe scripts/compute_example_households.py

# Python tests
.venv/Scripts/python.exe -m pytest tests
```

All outputs land in `frontend/public/data/` and are committed. The map
geojson (`frontend/public/data/geojson/`) is national 119th-Congress data and
already includes Colorado's 8 districts (`DISTRICT_ID` CO-01..CO-08).

## Frontend

`frontend/` is a Next.js (App Router) + Tailwind v4 single-page dashboard
with five tabs (`TAB_CONFIG` in `app/(shell)/page.tsx`):

1. **Policy overview** — the six-bracket table, who is affected, effective
   dates, and the Amendment 87 ballot designation.
2. **Household impact** — live calculator against
   `https://api.policyengine.org/us/calculate` (no backend server): baseline
   vs. the single contrib-parameter reform, state `CO`, tax year 2027,
   employment-income sweep to $1,300,000 so all six brackets are visible.
   Precomputed example-household cards load instantly from
   `public/data/example_households.json`.
3. **Statewide impact** — precomputed Modal results (revenue, distributional,
   winners/losers, poverty) read from the plain-named CSVs in
   `public/data/` per `scripts/DATA_SCHEMA.md`.
4. **Congressional districts** — SVG choropleth plus table for CO-01..CO-08,
   reading `congressional_districts.csv` and the committed geojson.
5. **Validation & methodology** — model revenue vs. the Legislative Council
   Staff fiscal impact statement, methodology, and the known modeling
   limitations below.

Every tab that depends on precomputed data renders a clear "not yet
available" state until the pipelines have run, so the app builds and deploys
before the Modal precompute.

```bash
cd frontend
npm install
npm run dev    # http://localhost:3010 (set NEXT_PUBLIC_BASE_PATH="" for local dev)
npm test       # vitest
npm run build  # production build (basePath /us/co-initiative-195)
```

## Known modeling limitations

- The initiative's (1.8)(b) home-sale carve-out (section 121-excess gains
  taxed at a flat 4.4%) is not modeled: this understates tax for filers at or
  below $100,000 with such gains, has no effect between $100,000 and
  $500,000, and overstates tax above $500,000.
- The corporate schedule (Section 4) and TABOR / Colorado's Future Fund
  accounting (Section 5) are outside the household model's scope.
- Statewide and district results come from the same national pass on one
  file, so district totals aggregate consistently to statewide; district
  geography is PUMA-assigned, however, so households are placed in CD-119
  districts via PUMA-to-district mappings rather than exact addresses.

## Deploy

Vercel project `co-initiative-195`, multi-zone basePath
`/us/co-initiative-195` (`vercel deploy --prod --scope policy-engine`, plus
an appZoneRoutes entry).

Live: TBD.
