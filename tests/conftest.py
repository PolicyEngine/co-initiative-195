"""
Pytest configuration and shared fixtures for the Colorado Initiative 195
(Amendment 87) dashboard.
"""

import pytest


@pytest.fixture
def sample_household_params():
    """Sample Colorado single-filer household for testing."""
    return {
        "age_head": 28,
        "age_spouse": None,
        "dependent_ages": [],
        "income": 45000,
        "year": 2027,
        "max_earnings": 1300000,
        "state_code": "CO",
    }


@pytest.fixture
def married_household_params():
    """Sample Colorado married-with-children household for testing."""
    return {
        "age_head": 40,
        "age_spouse": 38,
        "dependent_ages": [6, 9],
        "income": 95000,
        "year": 2027,
        "max_earnings": 1300000,
        "state_code": "CO",
    }
