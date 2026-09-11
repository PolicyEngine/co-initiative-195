"""Aggregate impact calculations for Colorado Initiative 195 (Amendment 87).

Direction is FORWARD: baseline = current law (4.4% flat tax), reform =
Initiative 195 graduated schedule, so every change is
``reform - baseline``. Negative household net-income change means the
household pays more tax under the initiative; positive revenue impact
means the state collects more.
"""

import numpy as np
from policyengine_us import Microsimulation

from .reforms import create_co_reform

# Colorado state-level dataset on HuggingFace.
CO_DATASET = "hf://policyengine/policyengine-us-data/states/CO.h5"

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


def calculate_aggregate_impact(year: int = DEFAULT_YEAR) -> dict:
    """Calculate the Colorado statewide impact of Initiative 195.

    Args:
        year: Tax year (default 2027, the initiative's first year).

    Returns:
        Dictionary with budget, decile, intra_decile, poverty, and
        income-bracket fields. All change amounts are
        ``reform - baseline`` (Initiative 195 minus current law).
    """
    reform = create_co_reform()

    # Baseline = current law (flat 4.4%). Reform = Initiative 195.
    sim_baseline = Microsimulation(dataset=CO_DATASET)
    sim_reform = Microsimulation(dataset=CO_DATASET, reform=reform)

    # ===== FISCAL IMPACT =====
    # Colorado state income tax
    co_baseline = sim_baseline.calculate(
        "co_income_tax", period=year, map_to="household"
    )
    co_reform = sim_reform.calculate(
        "co_income_tax", period=year, map_to="household"
    )
    state_tax_revenue_impact = float((co_reform - co_baseline).sum())

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

    # Federal income tax (SALT / itemization interactions)
    fed_baseline = sim_baseline.calculate(
        "income_tax", period=year, map_to="household"
    )
    fed_reform = sim_reform.calculate(
        "income_tax", period=year, map_to="household"
    )
    federal_tax_revenue_impact = float((fed_reform - fed_baseline).sum())

    tax_revenue_impact = federal_tax_revenue_impact + state_tax_revenue_impact
    budgetary_impact = tax_revenue_impact  # no benefit spending

    # household_net_income change for all distributional analysis
    baseline_net_income = sim_baseline.calculate(
        "household_net_income", period=year, map_to="household"
    )
    reform_net_income = sim_reform.calculate(
        "household_net_income", period=year, map_to="household"
    )
    income_change = reform_net_income - baseline_net_income
    change_arr = np.array(income_change)
    baseline_net_income_arr = np.array(baseline_net_income)
    household_weight = sim_baseline.calculate("household_weight", period=year)
    weight_arr = np.array(household_weight)

    total_households = float(weight_arr.sum())
    avg_household_net_income_change = (
        float((change_arr * weight_arr).sum() / total_households)
        if total_households
        else 0.0
    )

    # ===== WINNERS / LOSERS =====
    winners = float(weight_arr[change_arr > 1].sum())
    losers = float(weight_arr[change_arr < -1].sum())
    beneficiary_mask = change_arr > 0
    beneficiaries = float(weight_arr[beneficiary_mask].sum())
    avg_benefit = (
        float(
            (change_arr[beneficiary_mask] * weight_arr[beneficiary_mask]).sum()
            / beneficiaries
        )
        if beneficiaries > 0
        else 0.0
    )

    winners_rate = winners / total_households * 100 if total_households else 0.0
    losers_rate = losers / total_households * 100 if total_households else 0.0

    # ===== INCOME DECILE ANALYSIS =====
    decile = sim_baseline.calculate(
        "household_income_decile", period=year, map_to="household"
    )

    decile_average = {}
    decile_relative = {}
    for d in range(1, 11):
        dmask = decile == d
        d_weight = weight_arr[dmask]
        d_count = float(d_weight.sum())
        if d_count > 0:
            d_baseline_sum = float(
                (baseline_net_income_arr[dmask] * d_weight).sum()
            )
            d_change_sum = float((change_arr[dmask] * d_weight).sum())
            decile_average[str(d)] = d_change_sum / d_count
            decile_relative[str(d)] = (
                d_change_sum / d_baseline_sum
                if d_baseline_sum != 0
                else 0.0
            )
        else:
            decile_average[str(d)] = 0.0
            decile_relative[str(d)] = 0.0

    # Intra-decile requires person-weighted proportions — drop to numpy.
    people_per_hh = sim_baseline.calculate(
        "household_count_people", period=year, map_to="household"
    )
    capped_baseline = np.maximum(baseline_net_income_arr, 1)
    rel_change_arr = change_arr / capped_baseline

    decile_arr = np.array(decile)
    people_weighted = np.array(people_per_hh) * weight_arr

    intra_decile_deciles = {label: [] for label in _INTRA_LABELS}
    for d in range(1, 11):
        dmask = decile_arr == d
        d_people = people_weighted[dmask]
        d_total_people = d_people.sum()
        d_rel = rel_change_arr[dmask]

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

    # ===== POVERTY IMPACT =====
    pov_bl = sim_baseline.calculate(
        "in_poverty", period=year, map_to="person"
    )
    pov_rf = sim_reform.calculate(
        "in_poverty", period=year, map_to="person"
    )
    poverty_baseline_rate = float(pov_bl.mean() * 100)
    poverty_reform_rate = float(pov_rf.mean() * 100)
    poverty_rate_change, poverty_percent_change = _poverty_metrics(
        poverty_baseline_rate, poverty_reform_rate
    )

    # Child / deep poverty need age filtering — numpy required.
    age_arr = np.array(sim_baseline.calculate("age", period=year))
    is_child = age_arr < 18
    pw_arr = np.array(sim_baseline.calculate("person_weight", period=year))
    child_w = pw_arr[is_child]
    total_child_w = child_w.sum()

    pov_bl_arr = np.array(pov_bl).astype(bool)
    pov_rf_arr = np.array(pov_rf).astype(bool)

    def _child_rate(arr):
        return float(
            (arr[is_child] * child_w).sum() / total_child_w * 100
        ) if total_child_w > 0 else 0.0

    child_poverty_baseline_rate = _child_rate(pov_bl_arr)
    child_poverty_reform_rate = _child_rate(pov_rf_arr)
    child_poverty_rate_change, child_poverty_percent_change = (
        _poverty_metrics(
            child_poverty_baseline_rate, child_poverty_reform_rate
        )
    )

    deep_bl = sim_baseline.calculate(
        "in_deep_poverty", period=year, map_to="person"
    )
    deep_rf = sim_reform.calculate(
        "in_deep_poverty", period=year, map_to="person"
    )
    deep_poverty_baseline_rate = float(deep_bl.mean() * 100)
    deep_poverty_reform_rate = float(deep_rf.mean() * 100)
    deep_poverty_rate_change, deep_poverty_percent_change = (
        _poverty_metrics(
            deep_poverty_baseline_rate, deep_poverty_reform_rate
        )
    )

    deep_bl_arr = np.array(deep_bl).astype(bool)
    deep_rf_arr = np.array(deep_rf).astype(bool)
    deep_child_poverty_baseline_rate = _child_rate(deep_bl_arr)
    deep_child_poverty_reform_rate = _child_rate(deep_rf_arr)
    deep_child_poverty_rate_change, deep_child_poverty_percent_change = (
        _poverty_metrics(
            deep_child_poverty_baseline_rate,
            deep_child_poverty_reform_rate,
        )
    )

    # ===== INCOME BRACKET BREAKDOWN =====
    agi = sim_baseline.calculate(
        "adjusted_gross_income", period=year, map_to="household"
    )
    agi_arr = np.array(agi)

    by_income_bracket = []
    for min_inc, max_inc, label in INCOME_BRACKETS:
        band_mask = (agi_arr >= min_inc) & (agi_arr < max_inc)
        band_households = float(weight_arr[band_mask].sum())
        band_beneficiaries = float(
            weight_arr[band_mask & beneficiary_mask].sum()
        )
        if band_households > 0:
            band_total = float(
                (change_arr[band_mask] * weight_arr[band_mask]).sum()
            )
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

    return {
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
