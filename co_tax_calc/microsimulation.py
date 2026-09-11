"""Aggregate impact calculations for Colorado Initiative 195 (Amendment 87).

Runs ONE national baseline and ONE national reform Microsimulation on
the Populace build P ACS local-area dataset (~1.6M households with
PUMA-assigned CD-119 / county / state geography) and derives BOTH the
statewide and the congressional-district results from that single pass.

Dataset provenance (single national file):
    repo_id  policyengine/populace-us (HF dataset repo)
    revision populace-us-2024-buildp-acs-local-592ae5d6-20260819T020303Z
    filename populace_us_2024_acs_local.h5
The household table carries ``state_fips`` (int; Colorado = 8) and
``congressional_district_geoid`` (int SSDD = state_fips * 100 +
district number, at-large = 00; Colorado = 801..808) -- both are
policyengine-us input variables, so they are read via
``sim.calculate`` (names verified empirically against the h5).

Direction is FORWARD: baseline = current law (4.4% flat tax), reform =
Initiative 195 graduated schedule, so every change is
``reform - baseline``. Negative household net-income change means the
household pays more tax under the initiative; positive revenue impact
means the state collects more.

Weighted statistics use the MicroSeries weighted methods returned by
``calculate(..., map_to=...)`` (sums/means are weight-aware); explicit
weight arrays are used only where per-group masking requires numpy.
"""

import numpy as np
from policyengine_us import Microsimulation

from .reforms import create_co_reform

# Populace build P ACS local-area dataset on HuggingFace (dataset repo).
POPULACE_REPO = "policyengine/populace-us"
POPULACE_REVISION = (
    "populace-us-2024-buildp-acs-local-592ae5d6-20260819T020303Z"
)
POPULACE_FILENAME = "populace_us_2024_acs_local.h5"

# Colorado geography: state FIPS 08; CD-119 geoids 801..808 (SSDD).
CO_STATE_FIPS = 8
CO_DISTRICT_GEOIDS = list(range(801, 809))

# Initiative 195's first tax year.
DEFAULT_YEAR = 2027

# Intra-decile bounds and labels (same as app-v2)
_INTRA_BOUNDS = [-np.inf, -0.05, -1e-3, 1e-3, 0.05, np.inf]
_INTRA_LABELS = [
    "Lose more than 5%",
    "Lose less than 5%",
    "No change",
    "Gain less than 5%",
    "Gain more than 5%",
]

# Household-AGI bands for income_brackets.csv. Extend past $1M so all
# six Initiative 195 brackets are visible.
INCOME_BRACKETS = [
    (0, 25_000, "$0 - $25k"),
    (25_000, 50_000, "$25k - $50k"),
    (50_000, 75_000, "$50k - $75k"),
    (75_000, 100_000, "$75k - $100k"),
    (100_000, 200_000, "$100k - $200k"),
    (200_000, 500_000, "$200k - $500k"),
    (500_000, 750_000, "$500k - $750k"),
    (750_000, 1_000_000, "$750k - $1M"),
    (1_000_000, float("inf"), "$1M+"),
]


def load_dataset_path() -> str:
    """Download (or reuse the cached) build P ACS local-area h5."""
    from huggingface_hub import hf_hub_download

    return hf_hub_download(
        repo_id=POPULACE_REPO,
        repo_type="dataset",
        revision=POPULACE_REVISION,
        filename=POPULACE_FILENAME,
    )


def _poverty_metrics(baseline_rate: float, reform_rate: float):
    """Return (rate change, percent change) for a poverty metric.

    ``rate_change = reform - baseline`` percentage points: negative
    means poverty falls under Initiative 195. ``percent_change`` is
    relative to the baseline (current-law) rate.
    """
    rate_change = reform_rate - baseline_rate
    percent_change = (
        rate_change / baseline_rate * 100 if baseline_rate > 0 else 0.0
    )
    return rate_change, percent_change


def _weighted_deciles(values: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """Assign Colorado-relative income deciles (1..10).

    Weighted decile boundaries are computed over the given (already
    CO-restricted) values so decile semantics match a state-level
    dataset: decile 1 = poorest tenth of Colorado households.
    """
    sorter = np.argsort(values)
    cum = np.cumsum(weights[sorter])
    total = cum[-1]
    bounds = np.interp(
        [total * q / 10 for q in range(1, 10)], cum, values[sorter]
    )
    return np.digitize(values, bounds) + 1  # 1..10


def calculate_impacts(year: int = DEFAULT_YEAR) -> dict:
    """Calculate statewide AND district Initiative 195 impacts.

    One national baseline pass + one national reform pass on the build
    P ACS local-area dataset; Colorado rows are selected by
    ``state_fips == 8`` and districts by ``congressional_district_geoid``
    in 801..808.

    Returns:
        ``{"statewide": {...}, "districts": [{...}, ...]}`` where the
        statewide dict matches the metrics/distributional/winners-
        losers/income-bracket contract and each district dict matches
        the congressional_districts.csv contract
        (scripts/DATA_SCHEMA.md). All changes are reform - baseline.
    """
    dataset_path = load_dataset_path()
    reform = create_co_reform()

    # Baseline = current law (flat 4.4%). Reform = Initiative 195.
    sim_baseline = Microsimulation(dataset=dataset_path)
    sim_reform = Microsimulation(dataset=dataset_path, reform=reform)

    # ===== GEOGRAPHY MASKS =====
    state_fips = np.array(
        sim_baseline.calculate("state_fips", period=year, map_to="household")
    )
    cd_geoid = np.array(
        sim_baseline.calculate(
            "congressional_district_geoid", period=year, map_to="household"
        )
    )
    co_mask = state_fips == CO_STATE_FIPS

    if not co_mask.any():
        raise RuntimeError(
            "Sanity check failed: no households with state_fips == 8 "
            "(Colorado) in the dataset. Geography columns may have "
            "changed -- introspect the h5."
        )
    co_geoids = set(np.unique(cd_geoid[co_mask]).tolist())
    if co_geoids != set(CO_DISTRICT_GEOIDS):
        raise RuntimeError(
            "Sanity check failed: Colorado congressional_district_geoid "
            f"values are {sorted(co_geoids)}, expected "
            f"{CO_DISTRICT_GEOIDS}. Geography encoding may have changed."
        )

    # ===== HOUSEHOLD-LEVEL QUANTITIES (national, then CO-masked) =====
    co_tax_baseline = np.array(
        sim_baseline.calculate("co_income_tax", period=year, map_to="household")
    )
    co_tax_reform = np.array(
        sim_reform.calculate("co_income_tax", period=year, map_to="household")
    )
    fed_baseline = np.array(
        sim_baseline.calculate("income_tax", period=year, map_to="household")
    )
    fed_reform = np.array(
        sim_reform.calculate("income_tax", period=year, map_to="household")
    )
    net_income_baseline = np.array(
        sim_baseline.calculate(
            "household_net_income", period=year, map_to="household"
        )
    )
    net_income_reform = np.array(
        sim_reform.calculate(
            "household_net_income", period=year, map_to="household"
        )
    )
    agi = np.array(
        sim_baseline.calculate(
            "adjusted_gross_income", period=year, map_to="household"
        )
    )
    people_per_hh = np.array(
        sim_baseline.calculate(
            "household_count_people", period=year, map_to="household"
        )
    )
    hh_weight = np.array(
        sim_baseline.calculate("household_weight", period=year)
    )

    # CO-restricted arrays.
    w = hh_weight[co_mask]
    tax_delta = (co_tax_reform - co_tax_baseline)[co_mask]
    fed_delta = (fed_reform - fed_baseline)[co_mask]
    change = (net_income_reform - net_income_baseline)[co_mask]
    baseline_net = net_income_baseline[co_mask]
    co_agi = agi[co_mask]
    co_people = people_per_hh[co_mask]
    co_geoid = cd_geoid[co_mask]

    state_tax_revenue_impact = float((tax_delta * w).sum())

    # Sanity check: the reform must move CO income-tax revenue. A zero
    # delta means the contrib flag did not activate (e.g. a stale pin).
    if abs(state_tax_revenue_impact) < 1.0:
        raise RuntimeError(
            "Sanity check failed: Initiative 195 reform produced no "
            "change in CO income-tax revenue. Check that the installed "
            "policyengine-us release includes PR #9431 and the "
            "gov.contrib.states.co.progressive_income_tax.in_effect "
            "parameter."
        )

    federal_tax_revenue_impact = float((fed_delta * w).sum())
    tax_revenue_impact = federal_tax_revenue_impact + state_tax_revenue_impact
    budgetary_impact = tax_revenue_impact  # no benefit spending

    total_households = float(w.sum())
    avg_household_net_income_change = (
        float((change * w).sum() / total_households)
        if total_households
        else 0.0
    )

    # ===== WINNERS / LOSERS =====
    winners = float(w[change > 1].sum())
    losers = float(w[change < -1].sum())
    beneficiary_mask = change > 0
    beneficiaries = float(w[beneficiary_mask].sum())
    avg_benefit = (
        float((change[beneficiary_mask] * w[beneficiary_mask]).sum() / beneficiaries)
        if beneficiaries > 0
        else 0.0
    )
    winners_rate = winners / total_households * 100 if total_households else 0.0
    losers_rate = losers / total_households * 100 if total_households else 0.0

    # ===== INCOME DECILE ANALYSIS (Colorado-relative deciles) =====
    decile = _weighted_deciles(baseline_net, w)

    decile_average = {}
    decile_relative = {}
    for d in range(1, 11):
        dmask = decile == d
        d_weight = w[dmask]
        d_count = float(d_weight.sum())
        if d_count > 0:
            d_baseline_sum = float((baseline_net[dmask] * d_weight).sum())
            d_change_sum = float((change[dmask] * d_weight).sum())
            decile_average[str(d)] = d_change_sum / d_count
            decile_relative[str(d)] = (
                d_change_sum / d_baseline_sum if d_baseline_sum != 0 else 0.0
            )
        else:
            decile_average[str(d)] = 0.0
            decile_relative[str(d)] = 0.0

    # Intra-decile person-weighted proportions.
    capped_baseline = np.maximum(baseline_net, 1)
    rel_change = change / capped_baseline
    people_weighted = co_people * w

    intra_decile_deciles = {label: [] for label in _INTRA_LABELS}
    for d in range(1, 11):
        dmask = decile == d
        d_people = people_weighted[dmask]
        d_total_people = d_people.sum()
        d_rel = rel_change[dmask]
        for lower, upper, label in zip(
            _INTRA_BOUNDS[:-1], _INTRA_BOUNDS[1:], _INTRA_LABELS
        ):
            in_group = (d_rel > lower) & (d_rel <= upper)
            proportion = (
                float(d_people[in_group].sum() / d_total_people)
                if d_total_people > 0
                else 0.0
            )
            intra_decile_deciles[label].append(proportion)

    intra_decile_all = {
        label: sum(intra_decile_deciles[label]) / 10
        for label in _INTRA_LABELS
    }

    # ===== POVERTY IMPACT (person level, CO persons) =====
    person_state_fips = np.array(
        sim_baseline.calculate("state_fips", period=year, map_to="person")
    )
    person_cd_geoid = np.array(
        sim_baseline.calculate(
            "congressional_district_geoid", period=year, map_to="person"
        )
    )
    person_co_mask = person_state_fips == CO_STATE_FIPS
    pw = np.array(sim_baseline.calculate("person_weight", period=year))
    age = np.array(sim_baseline.calculate("age", period=year))
    pov_bl = np.array(
        sim_baseline.calculate("in_poverty", period=year, map_to="person")
    ).astype(bool)
    pov_rf = np.array(
        sim_reform.calculate("in_poverty", period=year, map_to="person")
    ).astype(bool)
    deep_bl = np.array(
        sim_baseline.calculate("in_deep_poverty", period=year, map_to="person")
    ).astype(bool)
    deep_rf = np.array(
        sim_reform.calculate("in_deep_poverty", period=year, map_to="person")
    ).astype(bool)

    def _rate(flag: np.ndarray, mask: np.ndarray) -> float:
        """Weighted percent of persons in ``mask`` with ``flag`` set."""
        denom = pw[mask].sum()
        return float((flag[mask] * pw[mask]).sum() / denom * 100) if denom > 0 else 0.0

    is_child = age < 18
    co_persons = person_co_mask
    co_children = person_co_mask & is_child

    poverty_baseline_rate = _rate(pov_bl, co_persons)
    poverty_reform_rate = _rate(pov_rf, co_persons)
    poverty_rate_change, poverty_percent_change = _poverty_metrics(
        poverty_baseline_rate, poverty_reform_rate
    )
    child_poverty_baseline_rate = _rate(pov_bl, co_children)
    child_poverty_reform_rate = _rate(pov_rf, co_children)
    child_poverty_rate_change, child_poverty_percent_change = _poverty_metrics(
        child_poverty_baseline_rate, child_poverty_reform_rate
    )
    deep_poverty_baseline_rate = _rate(deep_bl, co_persons)
    deep_poverty_reform_rate = _rate(deep_rf, co_persons)
    deep_poverty_rate_change, deep_poverty_percent_change = _poverty_metrics(
        deep_poverty_baseline_rate, deep_poverty_reform_rate
    )
    deep_child_poverty_baseline_rate = _rate(deep_bl, co_children)
    deep_child_poverty_reform_rate = _rate(deep_rf, co_children)
    deep_child_poverty_rate_change, deep_child_poverty_percent_change = (
        _poverty_metrics(
            deep_child_poverty_baseline_rate, deep_child_poverty_reform_rate
        )
    )

    # ===== INCOME BRACKET BREAKDOWN =====
    by_income_bracket = []
    for min_inc, max_inc, label in INCOME_BRACKETS:
        band_mask = (co_agi >= min_inc) & (co_agi < max_inc)
        band_households = float(w[band_mask].sum())
        band_beneficiaries = float(w[band_mask & beneficiary_mask].sum())
        if band_households > 0:
            band_total = float((change[band_mask] * w[band_mask]).sum())
            band_avg = band_total / band_households
        else:
            band_total = 0.0
            band_avg = 0.0
        by_income_bracket.append({
            "bracket": label,
            "households": band_households,
            "beneficiaries": band_beneficiaries,
            "total_cost": band_total,
            "avg_benefit": band_avg,
        })

    statewide = {
        "budget": {
            "budgetary_impact": budgetary_impact,
            "federal_tax_revenue_impact": federal_tax_revenue_impact,
            "state_tax_revenue_impact": state_tax_revenue_impact,
            "tax_revenue_impact": tax_revenue_impact,
            "households": total_households,
        },
        "decile": {
            "average": decile_average,
            "relative": decile_relative,
        },
        "intra_decile": {
            "all": intra_decile_all,
            "deciles": intra_decile_deciles,
        },
        "total_cost": -budgetary_impact,
        "avg_household_net_income_change": avg_household_net_income_change,
        "beneficiaries": beneficiaries,
        "avg_benefit": avg_benefit,
        "winners": winners,
        "losers": losers,
        "winners_rate": winners_rate,
        "losers_rate": losers_rate,
        "poverty_baseline_rate": poverty_baseline_rate,
        "poverty_reform_rate": poverty_reform_rate,
        "poverty_rate_change": poverty_rate_change,
        "poverty_percent_change": poverty_percent_change,
        "child_poverty_baseline_rate": child_poverty_baseline_rate,
        "child_poverty_reform_rate": child_poverty_reform_rate,
        "child_poverty_rate_change": child_poverty_rate_change,
        "child_poverty_percent_change": child_poverty_percent_change,
        "deep_poverty_baseline_rate": deep_poverty_baseline_rate,
        "deep_poverty_reform_rate": deep_poverty_reform_rate,
        "deep_poverty_rate_change": deep_poverty_rate_change,
        "deep_poverty_percent_change": deep_poverty_percent_change,
        "deep_child_poverty_baseline_rate": deep_child_poverty_baseline_rate,
        "deep_child_poverty_reform_rate": deep_child_poverty_reform_rate,
        "deep_child_poverty_rate_change": deep_child_poverty_rate_change,
        "deep_child_poverty_percent_change": deep_child_poverty_percent_change,
        "by_income_bracket": by_income_bracket,
    }

    # ===== DISTRICTS (same national pass, grouped by CD geoid) =====
    districts = []
    for geoid in CO_DISTRICT_GEOIDS:
        district_number = geoid % 100
        district_id = f"CO-{district_number:02d}"
        dmask = co_geoid == geoid
        dw = w[dmask]
        total_weight = float(dw.sum())

        d_change = change[dmask]
        d_baseline_net = baseline_net[dmask]
        d_tax_delta = tax_delta[dmask]

        if total_weight > 0:
            avg_change = float((d_change * dw).sum() / total_weight)
            avg_baseline = float((d_baseline_net * dw).sum() / total_weight)
            rel_change_d = avg_change / avg_baseline if avg_baseline > 0 else 0.0
            winners_share = float(dw[d_change > 1].sum() / total_weight)
            losers_share = float(dw[d_change < -1].sum() / total_weight)
        else:
            avg_change = 0.0
            rel_change_d = 0.0
            winners_share = 0.0
            losers_share = 0.0

        d_revenue = float((d_tax_delta * dw).sum())

        d_persons = person_cd_geoid == geoid
        d_children = d_persons & is_child
        d_pov_bl = _rate(pov_bl, d_persons)
        d_pov_rf = _rate(pov_rf, d_persons)
        poverty_pct_change = (
            (d_pov_rf - d_pov_bl) / d_pov_bl * 100 if d_pov_bl > 0 else 0.0
        )
        d_cpov_bl = _rate(pov_bl, d_children)
        d_cpov_rf = _rate(pov_rf, d_children)
        child_poverty_pct_change = (
            (d_cpov_rf - d_cpov_bl) / d_cpov_bl * 100 if d_cpov_bl > 0 else 0.0
        )

        districts.append({
            "district": district_id,
            "average_household_income_change": round(avg_change, 2),
            "relative_household_income_change": round(rel_change_d, 6),
            "winners_share": round(winners_share, 4),
            "losers_share": round(losers_share, 4),
            "affected_share": round(winners_share + losers_share, 4),
            "state_revenue_impact": round(d_revenue, 2),
            "poverty_pct_change": round(poverty_pct_change, 2),
            "child_poverty_pct_change": round(child_poverty_pct_change, 2),
            "state": "CO",
            "year": year,
        })

    return {"statewide": statewide, "districts": districts}


def calculate_aggregate_impact(year: int = DEFAULT_YEAR) -> dict:
    """Backward-compatible wrapper returning only the statewide dict."""
    return calculate_impacts(year=year)["statewide"]
