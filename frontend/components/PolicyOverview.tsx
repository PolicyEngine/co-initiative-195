'use client';

/** The six Initiative 195 brackets, applied to Colorado taxable income
 *  with the same thresholds for every filing status. */
export const CO_BRACKETS = [
  { range: '$0 – $25,000', rate: '3.7%' },
  { range: '$25,000 – $100,000', rate: '4.2%' },
  { range: '$100,000 – $500,000', rate: '4.4%' },
  { range: '$500,000 – $750,000', rate: '7.4%' },
  { range: '$750,000 – $1,000,000', rate: '7.9%' },
  { range: 'Over $1,000,000', rate: '8.4%' },
];

export default function PolicyOverview() {
  return (
    <div className="space-y-10">
      {/* Summary */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900 mb-4">
          Colorado Initiative 195 (Amendment 87)
        </h2>
        <p className="text-gray-700 mb-4">
          Colorado Initiative 2025&ndash;2026 #195, designated Amendment 87 on
          the November 2026 ballot, would replace Colorado&apos;s 4.4% flat
          individual income tax with six graduated brackets applied to
          Colorado taxable income, effective tax year 2027. The bracket
          thresholds are the same for all filing statuses.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
            <h3 className="font-semibold text-gray-800 mb-2">
              Graduated rates
            </h3>
            <p className="text-sm text-gray-600">
              Rates range from 3.7% on the first $25,000 of taxable income to
              8.4% on taxable income over $1,000,000, replacing the current
              4.4% flat rate.
            </p>
          </div>
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
            <h3 className="font-semibold text-gray-800 mb-2">
              Who is affected
            </h3>
            <p className="text-sm text-gray-600">
              Filers with taxable income below $100,000 face lower marginal
              rates on their first $100,000; the rate on taxable income
              between $100,000 and $500,000 is unchanged at 4.4%; filers with
              taxable income above $500,000 face higher marginal rates on
              income above that threshold.
            </p>
          </div>
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
            <h3 className="font-semibold text-gray-800 mb-2">
              Timing
            </h3>
            <p className="text-sm text-gray-600">
              On the statewide ballot in November 2026. If approved, the
              graduated schedule applies beginning tax year 2027. The measure
              also directs the added revenue to education and other named
              purposes.
            </p>
          </div>
        </div>
      </div>

      {/* Bracket table */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-3">
          Proposed rate schedule
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left py-3 px-4 font-semibold text-gray-900">Colorado taxable income</th>
                <th className="text-right py-3 px-4 font-semibold text-gray-900">Current law (flat)</th>
                <th className="text-right py-3 px-4 font-semibold text-gray-900">Initiative 195</th>
              </tr>
            </thead>
            <tbody>
              {CO_BRACKETS.map((b) => (
                <tr key={b.range} className="border-b border-gray-100">
                  <td className="py-3 px-4 text-gray-700">{b.range}</td>
                  <td className="py-3 px-4 text-right text-gray-700">4.4%</td>
                  <td className="py-3 px-4 text-right text-gray-700">{b.rate}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-xs text-gray-500 mt-2 italic">
          Marginal rates: each rate applies only to the taxable income within
          its bracket. The thresholds apply uniformly across filing statuses.
        </p>
      </div>

      {/* Scope / methodology */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-3">
          Scope of this dashboard
        </h3>
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 text-sm text-yellow-900">
          <p>
            The dashboard models the individual income-tax rate schedule in
            Sections 1&ndash;3 of the measure for tax year 2027. It does not
            model the measure&apos;s home-sale capital-gains carve-out, its
            corporate income-tax section, or its TABOR and revenue-allocation
            accounting; see the validation &amp; methodology tab for details.
            All figures are estimates comparing the graduated schedule with
            current law.
          </p>
        </div>
      </div>

      {/* References and further reading */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-3">
          References
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
            <h4 className="font-semibold text-gray-800 mb-2">Initiative 195</h4>
            <ul className="text-sm text-gray-700 space-y-1">
              <li>
                <a
                  href="https://www.sos.state.co.us/pubs/elections/Initiatives/titleBoard/filings/2025-2026/195Final.pdf"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary-600 hover:underline"
                >
                  Final text (Colorado Secretary of State)
                </a>
              </li>
              <li>
                <a
                  href="https://leg.colorado.gov/initiatives/graduated-income-tax-195"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary-600 hover:underline"
                >
                  Legislative Council Staff initiative page
                </a>
              </li>
            </ul>
          </div>
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
            <h4 className="font-semibold text-gray-800 mb-2">Calculations</h4>
            <p className="text-sm text-gray-700">
              Powered by{' '}
              <a
                href="https://github.com/PolicyEngine/policyengine-us"
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary-600 hover:underline"
              >
                policyengine-us
              </a>{' '}
              1.825.0 (the first release containing{' '}
              <a
                href="https://github.com/PolicyEngine/policyengine-us/pull/9431"
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary-600 hover:underline"
              >
                PR #9431
              </a>
              , which encodes the Initiative 195 rate schedule).
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
