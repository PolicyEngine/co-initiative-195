"""Colorado Initiative 195 (Amendment 87) calculation module.

Utilities for calculating household and aggregate impacts of Colorado
Initiative 195, which would replace Colorado's 4.4% flat income tax
with a six-bracket graduated schedule effective tax year 2027.

Direction is forward: baseline = current law (flat tax), reform =
Initiative 195 graduated schedule; impact = reform - baseline.
"""

from .household import build_household_situation, calculate_household_impact
from .reforms import (
    BASELINE_FLAT_RATE,
    BRACKETS,
    POLICYENGINE_US_PIN,
    REFORM_PARAMS,
    create_co_reform,
    graduated_tax,
)
from .microsimulation import calculate_aggregate_impact, calculate_impacts

__all__ = [
    "BASELINE_FLAT_RATE",
    "BRACKETS",
    "POLICYENGINE_US_PIN",
    "REFORM_PARAMS",
    "build_household_situation",
    "calculate_household_impact",
    "calculate_aggregate_impact",
    "calculate_impacts",
    "create_co_reform",
    "graduated_tax",
]

__version__ = "1.0.0"
