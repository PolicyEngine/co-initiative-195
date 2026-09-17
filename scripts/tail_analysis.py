"""Tabulate the CO subset's top-income tail vs SOI, and decompose the
Initiative 195 revenue estimate by bracket. Writes JSON to stdout-file."""

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from policyengine_us import Microsimulation
from co_tax_calc.reforms import create_co_reform, BRACKETS, BASELINE_FLAT_RATE

HERE = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.join(HERE, "..", "local_cache", "co_subset.h5")
OUT = os.path.join(HERE, "..", "local_cache", "tail_analysis.json")

out = {}

baseline = Microsimulation(dataset=DATASET)
reform = Microsimulation(dataset=DATASET, reform=create_co_reform())

# ---------- 2027 model-side tabulation ----------
YEAR = 2027
agi = baseline.calculate("adjusted_gross_income", period=YEAR)
cti = baseline.calculate("co_taxable_income", period=YEAR)
w = np.array(agi.weights)
agi_v = np.array(agi)
cti_v = np.array(cti)

base_tax = baseline.calculate("co_income_tax", period=YEAR)
ref_tax = reform.calculate("co_income_tax", period=YEAR)
out["baseline_co_income_tax_2027"] = float(base_tax.sum())
out["reform_co_income_tax_2027"] = float(ref_tax.sum())
out["revenue_impact_2027"] = float(ref_tax.sum() - base_tax.sum())
out["total_co_agi_2027"] = float(agi.sum())
out["total_co_taxable_income_2027"] = float(cti.sum())
out["n_tax_units_weighted"] = float(w.sum())
out["n_records"] = int(len(w))

# per-tax-unit reform delta (actual model, includes credit interactions)
delta = np.array(ref_tax) - np.array(base_tax)

BANDS = [
    ("0-25k", 0, 25e3),
    ("25-100k", 25e3, 100e3),
    ("100-500k", 100e3, 500e3),
    ("500-750k", 500e3, 750e3),
    ("750k-1M", 750e3, 1e6),
    ("1M+", 1e6, np.inf),
]


def band_table(measure_v, year_label):
    rows = []
    for label, lo, hi in BANDS:
        m = (measure_v >= lo) & (measure_v < hi)
        rows.append(
            {
                "band": label,
                "tax_units": float(w[m].sum()),
                "total_agi": float((w * agi_v)[m].sum()),
                "total_cti": float((w * cti_v)[m].sum()),
                "revenue_delta": float((w * delta)[m].sum()),
            }
        )
    return rows


out["bands_2027_by_co_taxable_income"] = band_table(cti_v, 2027)
out["bands_2027_by_agi"] = band_table(agi_v, 2027)

# Analytic marginal-revenue attribution by bracket segment (on CTI)
seg = {}
for i, (lo, rate) in enumerate(BRACKETS):
    hi = BRACKETS[i + 1][0] if i + 1 < len(BRACKETS) else np.inf
    inc_in_seg = np.clip(cti_v - lo, 0, hi - lo)
    seg[f"{lo}"] = {
        "rate": rate,
        "delta_rate": rate - BASELINE_FLAT_RATE,
        "marginal_revenue": float((w * (rate - BASELINE_FLAT_RATE) * inc_in_seg).sum()),
        "income_in_segment": float((w * inc_in_seg).sum()),
    }
out["segment_attribution_2027"] = seg
out["analytic_total_delta"] = float(sum(s["marginal_revenue"] for s in seg.values()))

# ---------- 2024 like-for-like SOI comparison (AGI at tax unit) ----------
agi24 = baseline.calculate("adjusted_gross_income", period=2024)
w24 = np.array(agi24.weights)
agi24_v = np.array(agi24)
tax_unit_filer = baseline.calculate("tax_unit_is_filer", period=2024) if "tax_unit_is_filer" in baseline.tax_benefit_system.variables else None

SOI_BANDS = [
    ("under_25k", -np.inf, 25e3),
    ("25-50k", 25e3, 50e3),
    ("50-75k", 50e3, 75e3),
    ("75-100k", 75e3, 100e3),
    ("100-200k", 100e3, 200e3),
    ("200-500k", 200e3, 500e3),
    ("500k-1M", 500e3, 1e6),
    ("1M+", 1e6, np.inf),
]
rows = []
for label, lo, hi in SOI_BANDS:
    m = (agi24_v >= lo) & (agi24_v < hi)
    row = {
        "band": label,
        "tax_units": float(w24[m].sum()),
        "total_agi": float((w24 * agi24_v)[m].sum()),
    }
    if tax_unit_filer is not None:
        f = np.array(tax_unit_filer, dtype=bool)
        row["filers"] = float(w24[m & f].sum())
        row["filer_agi"] = float((w24 * agi24_v)[m & f].sum())
    rows.append(row)
out["bands_2024_by_agi"] = rows
out["total_co_agi_2024"] = float(agi24.sum())
out["has_filer_var"] = tax_unit_filer is not None

# also 500-750/750-1M/1M+ granularity for 2024
rows2 = []
for label, lo, hi in [("500-750k", 5e5, 7.5e5), ("750k-1M", 7.5e5, 1e6), ("1M+", 1e6, np.inf)]:
    m = (agi24_v >= lo) & (agi24_v < hi)
    rows2.append({
        "band": label,
        "tax_units": float(w24[m].sum()),
        "total_agi": float((w24 * agi24_v)[m].sum()),
    })
out["bands_2024_top_detail"] = rows2

with open(OUT, "w") as fh:
    json.dump(out, fh, indent=2)
print("WROTE", OUT)
