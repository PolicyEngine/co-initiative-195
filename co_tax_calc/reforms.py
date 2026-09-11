"""Reform definition for the Colorado Initiative 195 (Amendment 87) dashboard.

Colorado Initiative 195 (ballot designation "Amendment 87", November
2026 ballot) replaces Colorado's 4.4% flat income tax with a six-bracket
graduated schedule on Colorado taxable income, uniform across filing
statuses, effective for taxable years commencing on or after
January 1, 2027.

The reform is modeled in policyengine-us as a contributed parameter
(PR #9431, first released in 1.825.0): setting
``gov.contrib.states.co.progressive_income_tax.in_effect`` to true
switches ``co_income_tax_before_non_refundable_credits`` from the flat
rate to the graduated schedule.

Direction is FORWARD: baseline = current law (flat 4.4%), reform =
Initiative 195 graduated schedule. Everywhere in this repository,
``impact = reform - baseline`` (a negative net-income change means the
household pays more tax under the initiative).
"""

from __future__ import annotations

from typing import Any, Dict

# Exact policyengine-us pin — first release containing PR #9431
# (Colorado Initiative 195 graduated income tax contributed reform).
# Mirrored in pyproject.toml, scripts/modal_pipeline.py, and
# scripts/modal_district_pipeline.py. Keep all four in sync.
POLICYENGINE_US_PIN = "policyengine-us==1.825.0"

# The single parameter override that activates Initiative 195.
REFORM_PARAMS: Dict[str, Dict[str, Any]] = {
    "gov.contrib.states.co.progressive_income_tax.in_effect": {
        "2027-01-01.2100-12-31": True,
    },
}

# Initiative 195 graduated schedule (Section 3, C.R.S. 39-22-104
# (1.8)(a)): marginal rates on Colorado taxable income, all filing
# statuses. (threshold, rate) pairs; each rate applies to income above
# its threshold up to the next threshold.
BRACKETS: list[tuple[int, float]] = [
    (0, 0.037),
    (25_000, 0.042),
    (100_000, 0.044),
    (500_000, 0.074),
    (750_000, 0.079),
    (1_000_000, 0.084),
]

# Current-law Colorado flat rate (baseline).
BASELINE_FLAT_RATE = 0.044


def create_co_reform():
    """Build the forward Initiative 195 reform.

    Returns a PolicyEngine ``Reform`` that sets the contrib in_effect
    flag from 2027 on. ``Reform.from_dict`` applies contributed
    parameter overrides directly in Python simulations.
    """
    from policyengine_core.reforms import Reform

    return Reform.from_dict(REFORM_PARAMS, country_id="us")


def graduated_tax(taxable_income: float) -> float:
    """Hand-computable Initiative 195 tax on Colorado taxable income.

    Reference implementation of the bracket math used by tests to
    cross-check the model (e.g. $300,000 taxable ->
    25,000*0.037 + 75,000*0.042 + 200,000*0.044 = $12,875).
    """
    tax = 0.0
    for i, (threshold, rate) in enumerate(BRACKETS):
        upper = (
            BRACKETS[i + 1][0] if i + 1 < len(BRACKETS) else float("inf")
        )
        if taxable_income <= threshold:
            break
        tax += (min(taxable_income, upper) - threshold) * rate
    return tax
