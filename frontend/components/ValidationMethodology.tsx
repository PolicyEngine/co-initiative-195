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

  // Model revenue = change in Colorado state tax collections under the
  // reform (positive = revenue increase). Wired to metrics.csv; shows a
  // pending state until the Modal precompute lands.
  const modelRevenue = data?.budget?.state_tax_revenue_impact ?? null;
  const diffVsOfficial =
    modelRevenue !== null
      ? (modelRevenue - OFFICIAL.fy2028FullYear) / OFFICIAL.fy2028FullYear
      : null;

  return (
    <div className="space-y-8">
      {/* Model vs official estimate */}
      <section>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          Model estimate vs. official fiscal impact statement
        </h2>
        <p className="text-gray-700 mb-6">
          Colorado&apos;s Legislative Council Staff published a fiscal impact
          statement for Initiative 195 estimating the state revenue increase
          from the graduated schedule. The comparison below places the
          model&apos;s tax year {CO_DASHBOARD_YEAR} estimate next to the
          official figures.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-5">
            <p className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">
              Official estimate (Legislative Council Staff)
            </p>
            <p className="text-sm text-gray-500">
              State revenue increase, FY 2027-28 (first full fiscal year)
            </p>
            <p className="text-3xl font-bold text-gray-900 tabular-nums mb-3">
              {formatBillions(OFFICIAL.fy2028FullYear)}
            </p>
            <p className="text-sm text-gray-500">
              FY 2026-27 (half-year of tax year 2027)
            </p>
            <p className="text-2xl font-bold text-gray-900 tabular-nums mb-3">
              {formatBillions(OFFICIAL.fy2027HalfYear)}
            </p>
            <p className="text-xs text-gray-500">
              The statement also reports a maximum dollar change of{' '}
              {formatBillions(OFFICIAL.maxDollarChange)} in FY 2027-28 and
              notes the increased revenue is exempt from TABOR as a
              voter-approved revenue change.
            </p>
          </div>

          <div className="bg-gray-50 border border-gray-200 rounded-lg p-5">
            <p className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">
              PolicyEngine model
            </p>
            <p className="text-sm text-gray-500">
              Colorado income-tax revenue change, tax year {CO_DASHBOARD_YEAR}
            </p>
            {modelRevenue !== null ? (
              <>
                <p className="text-3xl font-bold text-primary-600 tabular-nums mb-3">
                  {formatBillions(modelRevenue)}
                </p>
                {diffVsOfficial !== null && (
                  <span className="inline-block px-3 py-1 rounded-full text-xs font-semibold bg-primary-100 text-primary-700 tabular-nums">
                    {diffVsOfficial >= 0 ? '+' : '−'}
                    {Math.abs(diffVsOfficial * 100).toFixed(1)}% vs. FY 2027-28
                    official estimate
                  </span>
                )}
              </>
            ) : (
              <p className="text-lg font-semibold text-gray-400 mb-3">
                Pending — populated from metrics.csv once the Modal
                precompute has run
              </p>
            )}
          </div>
        </div>

        <p className="text-sm text-gray-600 mt-3">
          The two figures use different accounting periods: the model
          estimates calendar tax year {CO_DASHBOARD_YEAR} liability, while the
          official estimate is stated by state fiscal year (July&ndash;June),
          with FY 2027-28 the first full fiscal year of collections. The
          official estimate also excludes the effects of 2025 H.R. 1 (the
          &quot;One Big Beautiful Bill Act&quot;), which the fiscal impact
          statement notes it could not incorporate, while the PolicyEngine
          baseline includes it. Differences of this scale in comparison
          period and baseline mean an exact match is not expected.
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
              schedule only.
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
