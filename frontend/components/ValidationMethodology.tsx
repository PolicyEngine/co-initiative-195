'use client';

import { useAggregateImpact } from '@/hooks/useAggregateImpact';
import { CO_DASHBOARD_YEAR } from '@/lib/household';

/**
 * Validation & methodology tab, modeled on the FUTA wage-base
 * dashboard's validation tab: compare the model's revenue estimate with
 * the official Legislative Council Staff fiscal impact statement, then
 * document methodology, sources, and known modeling limitations.
 */

// Official estimate: Legislative Council Staff, Initiative 195 Fiscal
// Impact Statement (March 9, 2026). Full-year figure is FY 2027-28;
// the FY 2026-27 figure is a half-year impact of tax year 2027.
const OFFICIAL = {
  source:
    'Legislative Council Staff, Initiative 195 fiscal impact statement (March 9, 2026)',
  url: 'https://leg.colorado.gov/initiative_files/3320/download',
  fy2027HalfYear: 963_200_000, // FY 2026-27 (half-year of TY 2027)
  fy2028FullYear: 1_981_100_000, // FY 2027-28 (first full fiscal year)
  maxDollarChange: 2_700_000_000, // required forecast-error bound, FY 2027-28
};

const MODEL_INFO = {
  policyengineUs: '1.825.0',
  pin: 'policyengine-us==1.825.0 (first release containing PR #9431)',
};

const formatBillions = (value: number) => {
  const abs = Math.abs(value);
  const sign = value < 0 ? '-' : '';
  if (abs >= 1e9) return `${sign}$${(abs / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `${sign}$${(abs / 1e6).toFixed(0)}M`;
  return `${sign}$${abs.toLocaleString('en-US', { maximumFractionDigits: 0 })}`;
};

export default function ValidationMethodology() {
  const { data } = useAggregateImpact(true, CO_DASHBOARD_YEAR);

  // Model revenue = change in Colorado state income-tax collections
  // under the reform (positive = revenue increase). Wired to
  // metrics.csv; shows a pending state until the Modal precompute lands.
  const modelRevenue = data?.budget?.state_tax_revenue_impact ?? null;

  const comparisonRows = [
    {
      label: 'PolicyEngine household model, tax year 2027',
      amount:
        modelRevenue !== null ? formatBillions(modelRevenue) : 'Pending',
      note: 'Individual income tax only; lower bound (see below)',
      highlight: true,
    },
    {
      label: 'Model, adjusted for SOI top-tail coverage',
      amount: '≈$1.9B',
      note: "Scales the model's upper-bracket revenue by the IRS SOI income coverage ratio",
      highlight: false,
    },
    {
      label: 'LCS estimate, tax year 2027 annualized',
      amount: '≈$1.93B',
      note: '2 × the FY 2026-27 half-year figure; includes individual and corporate taxpayers',
      highlight: false,
    },
    {
      label: 'LCS estimate, FY 2027-28',
      amount: '$1,981.1M',
      note: 'First full fiscal year; includes individual and corporate taxpayers',
      highlight: false,
    },
  ];

  return (
    <div className="space-y-8">
      {/* Model vs official estimate */}
      <section>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          Model estimate vs. official fiscal impact statement
        </h2>
        <p className="text-gray-700 mb-6">
          Colorado&apos;s Legislative Council Staff (LCS) fiscal impact
          statement estimates the measure raises state revenue by $963.2
          million in FY 2026-27 (a half-year impact of tax year 2027) and
          $1,981.1 million in FY 2027-28, with a TABOR-required maximum of
          $2.7 billion; the added revenue is exempt from TABOR as a
          voter-approved revenue change. The model&apos;s tax year{' '}
          {CO_DASHBOARD_YEAR} estimate sits below the LCS figures for
          quantifiable reasons decomposed below.
        </p>

        <div className="overflow-x-auto mb-4">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-300">
                <th className="text-left px-4 py-3 font-medium text-gray-900">Estimate</th>
                <th className="text-right px-4 py-3 font-medium text-gray-900">Revenue increase</th>
                <th className="text-left px-4 py-3 font-medium text-gray-900">Basis</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {comparisonRows.map((row) => (
                <tr key={row.label} className={row.highlight ? 'bg-primary-50' : ''}>
                  <td className="px-4 py-3 text-gray-900">{row.label}</td>
                  <td
                    className={`px-4 py-3 text-right font-semibold tabular-nums ${
                      row.amount === 'Pending'
                        ? 'text-gray-400'
                        : row.highlight
                          ? 'text-primary-600'
                          : 'text-gray-900'
                    }`}
                  >
                    {row.amount}
                  </td>
                  <td className="px-4 py-3 text-gray-600">{row.note}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="bg-gray-50 border border-gray-200 rounded-lg p-5 mb-4">
          <p className="text-sm font-semibold text-gray-900 mb-2">
            Why the model figure is a lower bound on the individual side
          </p>
          <p className="text-sm text-gray-700 mb-2">
            The microdata&apos;s Colorado income distribution matches IRS SOI
            actuals on filer counts at high incomes — it carries 184% of
            SOI&apos;s count of returns with AGI over $1 million — but
            truncates income per filer: mean AGI in the $1M+ band is $1.27
            million in the model vs. $3.03 million in SOI (tax year 2023).
            Income mass above the $1 million threshold, which the top 8.4%
            bracket taxes, is $7.8 billion in the model vs. $31.7 billion in
            SOI — 24% coverage.
          </p>
          <p className="text-sm text-gray-700">
            Scaling the model&apos;s upper-bracket revenue by the SOI
            coverage ratio yields approximately $1.9 billion, within 5% of
            the LCS annualized estimate.
          </p>
        </div>

        <p className="text-sm text-gray-600">
          <strong>Scope and baseline differences.</strong> The LCS estimate
          covers both individual and corporate taxpayers — Section 4 of the
          measure applies the same rate schedule to C corporations, which is
          outside this household model&apos;s scope — and LCS publishes no
          individual/corporate split. Additional smaller differences: the
          LCS baseline excludes 2025 H.R. 1 (the &quot;One Big Beautiful
          Bill Act&quot;), which this model&apos;s baseline includes; the
          model is stated by tax year while the LCS figures are stated by
          state fiscal year; and both estimates are static, with no
          behavioral response.
        </p>
      </section>

      {/* Key modeling limitations */}
      <section>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          Key modeling limitations
        </h2>
        <p className="text-gray-700 mb-6">
          Three simplifications in how this dashboard represents Initiative
          195 are large enough to shape the results and deserve prominence.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-amber-50 border-l-4 border-amber-400 rounded-lg p-5">
            <p className="text-sm font-bold text-gray-900 mb-2">
              Home-sale carve-out unmodeled
            </p>
            <p className="text-sm text-gray-700">
              Section (1.8)(b) of the measure taxes gains from a primary-home
              sale in excess of the federal Section 121 exclusion at the flat
              4.4% rate rather than the graduated schedule. The model applies
              the graduated schedule to all taxable income, so for filers
              with such gains it understates tax below $100,000 of taxable
              income, has no effect between $100,000 and $500,000, and
              overstates tax above $500,000.
            </p>
          </div>
          <div className="bg-amber-50 border-l-4 border-amber-400 rounded-lg p-5">
            <p className="text-sm font-bold text-gray-900 mb-2">
              Corporate and TABOR sections out of scope
            </p>
            <p className="text-sm text-gray-700">
              The measure&apos;s corporate income-tax schedule (Section 4)
              and its TABOR / Colorado&apos;s Future Fund revenue-allocation
              accounting (Section 5) fall outside the household model&apos;s
              scope. All figures here cover the individual income-tax
              schedule only, while the LCS estimate includes both individual
              and corporate taxpayers.
            </p>
          </div>
          <div className="bg-amber-50 border-l-4 border-amber-400 rounded-lg p-5">
            <p className="text-sm font-bold text-gray-900 mb-2">
              District geography is PUMA-based
            </p>
            <p className="text-sm text-gray-700">
              Statewide and district figures come from the same single
              calibrated national dataset, so district totals sum to the
              statewide total up to rounding. Households are assigned to
              congressional districts via PUMA-based geography from the ACS
              multispine, which approximates district boundaries, so treat
              the split across districts as approximate.
            </p>
          </div>
        </div>
      </section>

      {/* Methodology and sources */}
      <section>
        <h2 className="text-2xl font-bold text-gray-900 mb-4">
          Methodology and sources
        </h2>
        <div className="space-y-3 text-sm text-gray-700">
          <p>
            <strong>Model and data.</strong> Estimates use{' '}
            <code className="text-xs bg-gray-100 px-1 py-0.5 rounded">
              {MODEL_INFO.pin}
            </code>
            , the first release containing the contributed Initiative 195
            rate schedule. Statewide and district results both come from a
            single calibrated national dataset: Populace build P ACS
            local-area (
            <code className="text-xs bg-gray-100 px-1 py-0.5 rounded">
              populace_us_2024_acs_local.h5
            </code>
            , revision{' '}
            <code className="text-xs bg-gray-100 px-1 py-0.5 rounded">
              populace-us-2024-buildp-acs-local-592ae5d6-20260819T020303Z
            </code>
            , ~1.6M households with PUMA-assigned 119th-Congress districts).
            Statewide figures filter to Colorado (state FIPS 08); district
            figures group the same file by congressional-district geoid
            (801&ndash;808).
          </p>
          <p>
            <strong>Reform definition.</strong> The baseline is current law
            (Colorado&apos;s 4.4% flat income tax). The reform switches on a
            single contributed parameter,{' '}
            <code className="text-xs bg-gray-100 px-1 py-0.5 rounded">
              gov.contrib.states.co.progressive_income_tax.in_effect
            </code>
            , from 2027 forward, which applies the six-bracket graduated
            schedule. Every figure on this dashboard is reform minus
            baseline for tax year {CO_DASHBOARD_YEAR}: positive state revenue
            changes are revenue increases, and negative household net-income
            changes are tax increases.
          </p>
          <p>
            <strong>Calibration coverage.</strong> The dataset calibrates
            Colorado aggregates tightly — total AGI is within +0.12% and
            total taxable income within &minus;0.10% of IRS SOI targets —
            but the calibration includes no income-amount targets above
            $500,000, so the top tail is uncalibrated in exactly the region
            the new 7.4%, 7.9%, and 8.4% brackets tax. This is the root
            cause of the lower-bound behavior quantified above. Per-target
            diagnostics are published on the{' '}
            <a
              href="https://calibration-diagnostics.vercel.app"
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary-600 hover:text-primary-700 underline"
            >
              calibration diagnostics dashboard
            </a>
            .
          </p>
          <p>
            <strong>Static estimate.</strong> No behavioral response is
            modeled: the estimates hold reported incomes fixed and do not
            capture changes in labor supply, capital-gains realization
            timing, tax planning, or migration. The official fiscal impact
            statement is likewise a static estimate.
          </p>
          <p>
            <strong>Poverty measures.</strong> Poverty impacts use the
            Supplemental Poverty Measure computed on the survey data. Survey
            data can overstate poverty levels, so emphasize the modeled
            changes rather than the levels.
          </p>
        </div>
        <ul className="mt-4 space-y-1 text-sm">
          {[
            {
              href: 'https://www.sos.state.co.us/pubs/elections/Initiatives/titleBoard/filings/2025-2026/195Final.pdf',
              text: 'Initiative 2025-2026 #195 final text (Colorado Secretary of State)',
            },
            {
              href: OFFICIAL.url,
              text: OFFICIAL.source,
            },
            {
              href: 'https://leg.colorado.gov/initiatives/graduated-income-tax-195',
              text: 'Legislative Council Staff initiative page (Initiative 195)',
            },
            {
              href: 'https://github.com/PolicyEngine/policyengine-us/pull/9431',
              text: 'policyengine-us PR #9431 — Colorado graduated income tax (contrib)',
            },
          ].map(({ href, text }) => (
            <li key={href}>
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary-600 hover:text-primary-700 underline"
              >
                {text}
              </a>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
