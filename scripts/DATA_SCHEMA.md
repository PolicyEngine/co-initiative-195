# Data contract — co-initiative-195 (Colorado Initiative 195 / Amendment 87)

Authoritative schema for every file the Python pipelines write into
`frontend/public/data/`. Builder B codes `frontend/lib` consumers against this
file. Produced by:

- `scripts/modal_pipeline.py` — ALL five CSVs (single merged Modal app: one
  national baseline + one national reform pass yields both the statewide CSVs
  and `congressional_districts.csv`)
- `scripts/compute_example_households.py` — `example_households.json` (local)

## Dataset provenance (microsimulation CSVs)

Single national Populace build P ACS local-area file (~1.6M households,
PUMA-assigned CD-119 / county / state geography), loaded FUTA-template style
(`hf_hub_download` then `Microsimulation(dataset=<path>)`):

- `repo_id`: `policyengine/populace-us` (HF **dataset** repo)
- `revision`: `populace-us-2024-buildp-acs-local-592ae5d6-20260819T020303Z`
- `filename`: `populace_us_2024_acs_local.h5`

Colorado rows: `state_fips == 8`. Districts: `congressional_district_geoid`
in 801..808 (integer SSDD = state FIPS × 100 + district number; verified
empirically against the h5).

**CO-subset step**: because Initiative 195 only affects Colorado, the
pipeline extracts the CO households (plus all their linked persons / tax
units / spm units / families / marital units, weights preserved — ~30–50k
households) from the national file into a CO-only `USSingleYearDataset` h5
BEFORE simulating, cached in the results Volume at
`cache/co_subset_<revision>.h5` so reruns skip the ~10GB national download.
Each household keeps its weight, so weighted CO statistics from the subset
are identical in meaning to CO-filtered statistics from a full national
run. Statewide and district results come from the same CO-only pass, so
district totals aggregate consistently to the statewide totals (unlike the
old per-district ECPS files, which were calibrated independently).

## Global conventions

- **Direction is FORWARD**: baseline = current law (4.4% flat tax), reform =
  Initiative 195 graduated schedule (contrib flag
  `gov.contrib.states.co.progressive_income_tax.in_effect` = true from
  2027-01-01).
- **Sign convention**: every "change"/"impact" value is `reform − baseline`.
  - Household/net-income quantities: **negative = the household pays more tax**
    under Initiative 195; positive = the household gains.
  - Revenue quantities (`*_revenue_impact`): expressed as *government revenue*
    change, i.e. `reform tax − baseline tax`; **positive = the state collects
    more revenue** under Initiative 195.
  - `budgetary_impact` (metrics.csv) is a revenue quantity (positive = revenue
    gain); `total_cost = −budgetary_impact` is the household-side mirror.
- **Year**: single tax year **2027** everywhere. The `year` column is retained
  for schema stability but always equals `2027`.
- **No `_revert` suffixes.** Files are `metrics.csv`,
  `distributional_impact.csv`, `winners_losers.csv`, `income_brackets.csv`,
  `congressional_districts.csv`, `example_households.json`.
- Pin: `policyengine-us==1.825.0` (first release containing PR #9431).

## metrics.csv (long format: one metric per row)

| column | meaning |
|---|---|
| `year` | 2027 |
| `metric` | metric name (below) |
| `value` | numeric value |

Metrics:

| metric | meaning / sign |
|---|---|
| `budgetary_impact` | total (federal + CO state) tax revenue change, $/yr; positive = revenue gain |
| `federal_tax_revenue_impact` | federal income tax revenue change (SALT / itemization interactions), $ |
| `state_tax_revenue_impact` | CO income tax revenue change, $; positive = Initiative 195 raises revenue |
| `tax_revenue_impact` | = federal + state revenue impact |
| `households` | weighted count of CO households |
| `avg_household_net_income_change` | mean household net-income change across ALL households, $; negative = average tax increase |
| `total_cost` | `−budgetary_impact` (aggregate household net-income change), $ |
| `beneficiaries` | weighted households with net-income change > 0 |
| `avg_benefit` | mean net-income change among beneficiaries only, $ (positive) |
| `winners` | weighted households gaining > $1 |
| `losers` | weighted households losing > $1 |
| `winners_rate` | winners / households × 100 (percent) |
| `losers_rate` | losers / households × 100 (percent) |
| `poverty_baseline_rate` | SPM poverty rate under current law, percent |
| `poverty_reform_rate` | SPM poverty rate under Initiative 195, percent |
| `poverty_rate_change` | `reform − baseline` percentage points; negative = poverty falls under the initiative |
| `poverty_percent_change` | `rate_change / baseline_rate × 100`, percent |
| `child_poverty_*`, `deep_poverty_*`, `deep_child_poverty_*` | same four fields for child / deep / deep-child poverty, same sign convention |

Note the poverty sign convention differs from the GA template (which used
`baseline − reform` in the revert direction): here **all** change metrics are
uniformly `reform − baseline`.

## distributional_impact.csv

One row per income decile.

| column | meaning |
|---|---|
| `year` | 2027 |
| `decile` | `1`..`10` — **Colorado-relative** decile (weighted deciles of baseline household net income computed among Colorado households, so decile 1 = poorest tenth of Colorado, not of the nation) |
| `average_change` | mean household net-income change in the decile, $ (negative = tax increase) |
| `relative_change` | decile total net-income change ÷ decile total baseline net income (fraction, e.g. `-0.004` = −0.4%) |

## winners_losers.csv

One row per decile plus an `All` row. Person-weighted shares; each row's five
share columns sum to 1.

| column | meaning |
|---|---|
| `year` | 2027 |
| `decile` | `All`, `1`..`10` |
| `gain_more_5pct` | share gaining > 5% of net income |
| `gain_less_5pct` | share gaining ≤ 5% |
| `no_change` | share with \|relative change\| ≤ 0.1% |
| `lose_less_5pct` | share losing ≤ 5% |
| `lose_more_5pct` | share losing > 5% |

## income_brackets.csv

One row per household-AGI band. Bands extend past $1M so all six Initiative
195 brackets are visible. Band labels (exact strings, in order):

`$0 - $25k`, `$25k - $50k`, `$50k - $75k`, `$75k - $100k`, `$100k - $200k`,
`$200k - $500k`, `$500k - $750k`, `$750k - $1M`, `$1M+`

| column | meaning |
|---|---|
| `year` | 2027 |
| `bracket` | band label above (household AGI, baseline) |
| `households` | weighted household count in the band |
| `beneficiaries` | weighted households in the band with net-income change > 0 (column name kept from the GA template) |
| `total_cost` | weighted SUM of net-income change over ALL households in the band, $; negative = band pays more tax in aggregate |
| `avg_benefit` | weighted MEAN net-income change over ALL households in the band, $; negative = average tax increase (name kept from GA template; recomputed forward over all households, not just gainers) |

## congressional_districts.csv

One row per district, CO-01..CO-08 (FIPS 08), year 2027.

| column | meaning |
|---|---|
| `district` | `CO-01`..`CO-08` |
| `average_household_income_change` | mean household net-income change, $ (negative = tax increase) |
| `relative_household_income_change` | avg change ÷ avg baseline net income (fraction) |
| `winners_share` | share of households gaining > $1 (fraction 0-1) |
| `losers_share` | share of households losing > $1 (fraction 0-1) |
| `affected_share` | `winners_share + losers_share` (fraction 0-1) |
| `state_revenue_impact` | district total CO income-tax revenue change, $; positive = more revenue |
| `poverty_pct_change` | SPM poverty percent change, `(reform − baseline)/baseline × 100`; negative = poverty falls |
| `child_poverty_pct_change` | same for children |
| `state` | `CO` |
| `year` | 2027 |

Provenance note (surface in the validation tab): districts come from the
SAME national pass as the statewide CSVs (grouped by
`congressional_district_geoid`), so district totals aggregate consistently
to statewide. The old "independently calibrated district files do not sum
to statewide" caveat no longer applies; the remaining caveat is that
district geography is PUMA-assigned (households are placed in CD-119
districts from PUMA-to-district mappings).

## example_households.json

```jsonc
{
  "year": 2027,
  "pin": "policyengine-us==1.825.0",
  "households": [
    {
      "label": "…",                       // display label
      "income": 95000,                    // employment income at the point estimate
      "age_head": 40,
      "married": true,
      "dependents": [6, 9],               // ages; [] if none
      // optional extra inputs a profile may carry (taxable_pension_income,
      // social_security_retirement, …) — informational only
      "baseline": {                       // current law (flat 4.4%)
        "household_net_income": 0.0,
        "co_income_tax": 0.0,
        "income_tax": 0.0                 // federal
      },
      "reform": { /* same three keys under Initiative 195 */ },
      "net_income_change": 0.0,           // reform − baseline; negative = pays more
      "state_tax_change": 0.0,            // co_income_tax reform − baseline; positive = pays MORE state tax
      "federal_tax_change": 0.0,          // federal income_tax reform − baseline
      "chart": {                          // employment-income sweep, $0..$1,300,000
        "income_range": [0, 10000, …],    // 131 points, $10k step
        "net_income_change": [ … ],       // reform − baseline at each point
        "state_tax_change": [ … ],        // positive = pays more CO tax
        "federal_tax_change": [ … ]
      }
    }
  ]
}
```

Signs: `net_income_change` is household-side (negative = worse off);
`state_tax_change` / `federal_tax_change` are tax-side (positive = pays more
tax). Typically `net_income_change ≈ −(state_tax_change + federal_tax_change)`.

Profiles include at least: single filer, married family with children,
retired couple, and one household above $1,000,000 so the top 8.4% bracket is
exercised. There is NO per-provision attribution (Initiative 195 is a single
provision) — the GA `provisions` / `provisions_chart` keys are gone.

## geojson (unchanged from template)

`frontend/public/data/geojson/congressional_districts.geojson` and
`congressional_districts_hex.geojson` are **national** 119th-Congress files
already containing all 8 Colorado districts. Filter features by
`properties.DISTRICT_ID` (`"CO-01"`..`"CO-08"`) or `properties.STATEFP ===
"08"` (choropleth) / `properties.STATEAB === "CO"` (hex).
