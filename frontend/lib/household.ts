/**
 * Build a PolicyEngine household situation for the PE API.
 *
 * For the Colorado Initiative 195 (Amendment 87) dashboard:
 * - The PolicyEngine baseline represents current law (Colorado's 4.4%
 *   flat income tax).
 * - The reform activates the contributed graduated-bracket schedule
 *   (policyengine-us PR #9431) via a single parameter switch.
 * - Sign convention everywhere: impact = reform - baseline. A negative
 *   net-income change means the household pays more tax under the
 *   graduated schedule.
 */

import type { HouseholdRequest } from "./types";

const GROUP_UNITS = ["families", "spm_units", "tax_units", "households"] as const;

/** Tax year the dashboard models (Initiative 195 takes effect TY 2027). */
export const CO_DASHBOARD_YEAR = 2027;

/** Default top of the income sweep — past the $1,000,000 bracket
 *  threshold so all six brackets are visible. */
export const CO_SWEEP_MAX = 1_300_000;

/**
 * Reform policy: turn on the contributed Colorado graduated income tax
 * (six brackets: 3.7% / 4.2% / 4.4% / 7.4% / 7.9% / 8.4% at
 * $0 / $25k / $100k / $500k / $750k / $1M), effective tax year 2027.
 * The PolicyEngine API applies this as a reform on top of current law.
 */
const REFORM_POLICY: Record<string, Record<string, number | boolean>> = {
  "gov.contrib.states.co.progressive_income_tax.in_effect": {
    "2027-01-01.2100-12-31": true,
  },
};

function addMemberToUnits(
  situation: Record<string, unknown>,
  memberId: string
): void {
  for (const unit of GROUP_UNITS) {
    const unitObj = situation[unit] as Record<string, { members: string[] }>;
    const key = Object.keys(unitObj)[0];
    unitObj[key].members.push(memberId);
  }
}

export function buildHouseholdSituation(
  params: HouseholdRequest
): Record<string, unknown> {
  const {
    age_head,
    age_spouse,
    dependent_ages,
    income,
    year,
    max_earnings,
    state_code,
  } = params;
  const effectiveStateCode = state_code || "CO";
  const yearStr = String(year);
  const axisMax = Math.max(max_earnings, income);

  const situation: Record<string, unknown> = {
    people: {
      you: {
        age: { [yearStr]: age_head },
        employment_income: { [yearStr]: null },
      },
    },
    families: { "your family": { members: ["you"] } },
    marital_units: { "your marital unit": { members: ["you"] } },
    spm_units: { "your household": { members: ["you"] } },
    tax_units: {
      "your tax unit": {
        members: ["you"],
        adjusted_gross_income: { [yearStr]: null },
        income_tax: { [yearStr]: null },
        co_income_tax: { [yearStr]: null },
      },
    },
    households: {
      "your household": {
        members: ["you"],
        state_code: { [yearStr]: effectiveStateCode },
        household_net_income: { [yearStr]: null },
      },
    },
    axes: [
      [
        {
          name: "employment_income",
          min: 0,
          max: axisMax,
          count: Math.min(4001, Math.max(501, Math.floor(axisMax / 500))),
          period: yearStr,
          target: "person",
        },
      ],
    ],
  };

  if (age_spouse != null) {
    const people = situation.people as Record<string, Record<string, unknown>>;
    people["your partner"] = { age: { [yearStr]: age_spouse } };
    addMemberToUnits(situation, "your partner");
    const maritalUnits = situation.marital_units as Record<string, { members: string[] }>;
    maritalUnits["your marital unit"].members.push("your partner");
  }

  for (let i = 0; i < dependent_ages.length; i++) {
    const childId =
      i === 0
        ? "your first dependent"
        : i === 1
          ? "your second dependent"
          : `dependent_${i + 1}`;

    const people = situation.people as Record<string, Record<string, unknown>>;
    people[childId] = { age: { [yearStr]: dependent_ages[i] } };
    addMemberToUnits(situation, childId);
    const maritalUnits = situation.marital_units as Record<string, { members: string[] }>;
    maritalUnits[`${childId}'s marital unit`] = {
      members: [childId],
    };
  }

  return situation;
}

/**
 * Build the Initiative 195 reform policy dict for the PE API.
 * The dashboard computes: impact = reform - baseline (current law).
 */
export function buildReformPolicy(): Record<string, Record<string, number | boolean>> {
  return REFORM_POLICY;
}

/**
 * Linear interpolation helper - find the value at `x` in sorted arrays.
 */
export function interpolate(
  xs: number[],
  ys: number[],
  x: number
): number {
  if (x <= xs[0]) return ys[0];
  if (x >= xs[xs.length - 1]) return ys[ys.length - 1];
  for (let i = 1; i < xs.length; i++) {
    if (xs[i] >= x) {
      const t = (x - xs[i - 1]) / (xs[i] - xs[i - 1]);
      return ys[i - 1] + t * (ys[i] - ys[i - 1]);
    }
  }
  return ys[ys.length - 1];
}
