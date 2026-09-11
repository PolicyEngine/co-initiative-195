"""Configuration checks for the merged Modal pipeline.

Guard the dataset provenance (Populace build P acs-local -- the old
hf://policyengine/policyengine-us-data repo is ARCHIVED and its
states/CO.h5 + districts/CO-0N.h5 files no longer exist), the exact
policyengine-us pin, and the single-app structure.
"""

from pathlib import Path

from co_tax_calc.microsimulation import (
    CO_DISTRICT_GEOIDS,
    CO_STATE_FIPS,
    POPULACE_FILENAME,
    POPULACE_REPO,
    POPULACE_REVISION,
)
from co_tax_calc.reforms import POLICYENGINE_US_PIN

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"


class TestDatasetProvenance:
    def test_populace_build_p_acs_local(self):
        assert POPULACE_REPO == "policyengine/populace-us"
        assert POPULACE_REVISION == (
            "populace-us-2024-buildp-acs-local-592ae5d6-20260819T020303Z"
        )
        assert POPULACE_FILENAME == "populace_us_2024_acs_local.h5"

    def test_colorado_geography_constants(self):
        assert CO_STATE_FIPS == 8
        assert CO_DISTRICT_GEOIDS == list(range(801, 809))

    def test_no_archived_dataset_urls_anywhere(self):
        """The archived policyengine-us-data HF repo must not be
        referenced by any Python source (its state/district h5 files
        404)."""
        sources = list(REPO_ROOT.glob("co_tax_calc/*.py")) + list(
            SCRIPTS.glob("*.py")
        )
        assert sources
        for src in sources:
            text = src.read_text(encoding="utf-8")
            assert "policyengine-us-data" not in text, (
                f"{src.name} references the archived "
                "policyengine/policyengine-us-data repo"
            )


class TestMergedPipeline:
    def test_district_pipeline_deleted(self):
        assert not (SCRIPTS / "modal_district_pipeline.py").exists(), (
            "modal_district_pipeline.py should be folded into "
            "modal_pipeline.py (single national pass)"
        )

    def test_pipeline_mirrors_pin(self):
        text = (SCRIPTS / "modal_pipeline.py").read_text(encoding="utf-8")
        assert f'POLICYENGINE_US_PIN = "{POLICYENGINE_US_PIN}"' in text

    def test_pipeline_is_ascii_safe(self):
        """Windows cp1252 consoles crash on non-ASCII prints from the
        Modal driver; keep the pipeline sources ASCII-only."""
        for name in ("modal_pipeline.py", "compute_example_households.py"):
            text = (SCRIPTS / name).read_text(encoding="utf-8")
            non_ascii = sorted({c for c in text if ord(c) > 127})
            assert not non_ascii, (
                f"{name} contains non-ASCII characters: "
                f"{[hex(ord(c)) for c in non_ascii]}"
            )
