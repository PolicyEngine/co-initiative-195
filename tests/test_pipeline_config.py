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


class TestDetachSafety:
    """The pipeline must survive local `modal run` driver death: the
    remote fn persists results to a committed Volume, kickoff is
    fire-and-forget (spawn), and a separate fetch entrypoint downloads
    the CSVs afterwards."""

    @property
    def text(self):
        return (SCRIPTS / "modal_pipeline.py").read_text(encoding="utf-8")

    def test_results_volume_attached_and_committed(self):
        text = self.text
        assert '"co-initiative-195-results"' in text
        assert "create_if_missing=True" in text
        assert "results_volume.commit()" in text
        assert "volumes={RESULTS_DIR: results_volume}" in text

    def test_manifest_written(self):
        text = self.text
        assert "manifest.json" in text
        for key in (
            '"generated_at_utc"',
            '"pin"',
            '"dataset_revision"',
            '"files"',
        ):
            assert key in text, f"manifest missing {key}"

    def test_kickoff_spawns_and_fetch_exists(self):
        text = self.text
        assert "def kickoff()" in text
        assert "compute.spawn(" in text, (
            "kickoff must spawn (fire-and-forget) so --detach survives "
            "local death"
        )
        assert "def fetch()" in text
        assert "modal run --detach scripts/modal_pipeline.py::kickoff" in text
        assert "modal run scripts/modal_pipeline.py::fetch" in text

    def test_subset_cached_in_volume(self):
        """The CO subset must be built before simulating and cached in
        the results Volume keyed by dataset revision."""
        text = self.text
        assert "build_co_subset" in text
        assert "CO_SUBSET_FILENAME" in text
        assert 'os.path.join(RESULTS_DIR, "cache")' in text


class TestBuildCoSubset:
    """Unit tests for the CO-subset extraction on a synthetic national
    dataset (no downloads)."""

    @staticmethod
    def _make_national(tmp_path, n_co=12_000, n_other=500):
        import numpy as np
        import pandas as pd
        from policyengine_us.data import USSingleYearDataset

        from co_tax_calc.microsimulation import (
            CO_DISTRICT_GEOIDS,
            CO_STATE_FIPS,
        )

        n = n_co + n_other
        hh_ids = np.arange(1, n + 1)
        state = np.where(np.arange(n) < n_co, CO_STATE_FIPS, 48)  # TX rest
        geoid = np.where(
            np.arange(n) < n_co,
            np.array(CO_DISTRICT_GEOIDS)[np.arange(n) % 8],
            4801,
        )
        household = pd.DataFrame({
            "household_id": hh_ids,
            "state_fips": state,
            "congressional_district_geoid": geoid,
            "household_weight": np.full(n, 25.0),
        })
        # One person + one of each group unit per household, ids = hh id.
        person = pd.DataFrame({
            "person_id": hh_ids,
            "person_household_id": hh_ids,
            "person_tax_unit_id": hh_ids,
            "person_spm_unit_id": hh_ids,
            "person_family_id": hh_ids,
            "person_marital_unit_id": hh_ids,
            "person_weight": np.full(n, 25.0),
            "age": np.full(n, 40),
        })
        national = USSingleYearDataset(
            person=person,
            household=household,
            tax_unit=pd.DataFrame({"tax_unit_id": hh_ids}),
            spm_unit=pd.DataFrame({"spm_unit_id": hh_ids}),
            family=pd.DataFrame({"family_id": hh_ids}),
            marital_unit=pd.DataFrame({"marital_unit_id": hh_ids}),
            time_period=2024,
        )
        path = str(tmp_path / "national.h5")
        national.save(path)
        return path

    def test_subset_keeps_only_colorado_with_weights(self, tmp_path):
        from policyengine_us.data import USSingleYearDataset

        from co_tax_calc.microsimulation import build_co_subset

        national_path = self._make_national(tmp_path)
        out_path = str(tmp_path / "co_subset.h5")
        n = build_co_subset(national_path, out_path)
        assert n == 12_000

        subset = USSingleYearDataset(file_path=out_path)
        assert (subset.household["state_fips"] == 8).all()
        assert len(subset.household) == 12_000
        assert len(subset.person) == 12_000
        assert len(subset.tax_unit) == 12_000
        assert len(subset.spm_unit) == 12_000
        # Weights carried through unchanged.
        assert (subset.household["household_weight"] == 25.0).all()
        # All 8 district geoids present.
        assert set(
            subset.household["congressional_district_geoid"].unique()
        ) == set(range(801, 809))
        assert subset.time_period == "2024"

    def test_subset_rejects_missing_district(self, tmp_path):
        import pandas as pd
        import pytest

        from co_tax_calc.microsimulation import build_co_subset

        national_path = self._make_national(tmp_path)
        # Break geography: rewrite the CO-08 rows to CO-01.
        with pd.HDFStore(national_path) as store:
            hh = store["household"]
            hh.loc[
                hh["congressional_district_geoid"] == 808,
                "congressional_district_geoid",
            ] = 801
            store.put("household", hh, format="table", data_columns=True)

        with pytest.raises(
            RuntimeError, match="congressional_district_geoid"
        ):
            build_co_subset(national_path, str(tmp_path / "co2.h5"))

    def test_subset_rejects_implausible_count(self, tmp_path):
        import pytest

        from co_tax_calc.microsimulation import build_co_subset

        national_path = self._make_national(tmp_path, n_co=800, n_other=50)
        with pytest.raises(RuntimeError, match="households"):
            build_co_subset(national_path, str(tmp_path / "co3.h5"))
