'use client';

import { useEffect, useState } from 'react';
import type { HouseholdImpactResponse } from '@/lib/types';

export interface ExampleHouseholdProfile {
  label: string;
  income: number;
  age_head: number;
  married: boolean;
  dependents: number[];
}

interface ChartArrays {
  income_range: number[];
  net_income_change: number[];
  state_tax_change: number[];
  federal_tax_change: number[];
}

interface ExampleHousehold extends ExampleHouseholdProfile {
  baseline: {
    household_net_income: number;
    co_income_tax: number;
    income_tax: number;
  };
  reform: {
    household_net_income: number;
    co_income_tax: number;
    income_tax: number;
  };
  net_income_change: number;
  state_tax_change: number;
  federal_tax_change?: number;
  chart: ChartArrays;
}

interface Payload {
  year: number;
  households: ExampleHousehold[];
}

const fmtCurrency = (v: number) =>
  `$${Math.round(v).toLocaleString('en-US')}`;

const fmtSigned = (v: number) => {
  const base = fmtCurrency(Math.abs(v));
  if (v > 0) return `+${base}`;
  if (v < 0) return `-${base}`;
  return base;
};

/** Build a HouseholdImpactResponse-shaped payload from one of the
 *  precomputed example records, so the existing ImpactAnalysis chart
 *  can render it without firing a live API call. */
function toImpactResponse(h: ExampleHousehold): HouseholdImpactResponse {
  const xMax = h.chart.income_range[h.chart.income_range.length - 1];
  const federalTaxChange =
    h.federal_tax_change ?? h.reform.income_tax - h.baseline.income_tax;
  return {
    income_range: h.chart.income_range,
    net_income_change: h.chart.net_income_change,
    federalTaxChange: h.chart.federal_tax_change,
    stateTaxChange: h.chart.state_tax_change,
    netIncomeChange: h.chart.net_income_change,
    benefit_at_income: {
      baseline: h.baseline.household_net_income,
      reform: h.reform.household_net_income,
      difference: h.net_income_change,
      federal_tax_change: federalTaxChange,
      state_tax_change: h.state_tax_change,
      net_income_change: h.net_income_change,
    },
    x_axis_max: xMax,
  };
}

interface Props {
  /** Fires when a card is clicked; parent populates the household form
   *  and passes the precomputed response into ImpactAnalysis. */
  onSelect: (
    profile: ExampleHouseholdProfile,
    response: HouseholdImpactResponse,
  ) => void;
  /** Label of the currently active example, so the matching card can
   *  highlight itself. */
  selectedLabel?: string | null;
}

export default function ExampleHouseholds({
  onSelect,
  selectedLabel,
}: Props) {
  const [data, setData] = useState<Payload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const basePath =
      process.env.NEXT_PUBLIC_BASE_PATH !== undefined
        ? process.env.NEXT_PUBLIC_BASE_PATH
        : '/us/co-initiative-195';
    fetch(`${basePath}/data/example_households.json`)
      .then((res) => {
        if (!res.ok) throw new Error(`Failed to load (${res.status})`);
        return res.json();
      })
      .then((j: Payload) => setData(j))
      .catch((e) => setError(e.message));
  }, []);

  // The examples are an optional enhancement; render nothing until the
  // precomputed payload exists.
  if (error) return null;
  if (!data) return null;

  return (
    <div>
      <h3 className="text-lg font-semibold text-gray-900 mb-1">
        Example households
      </h3>
      <p className="text-sm text-gray-600 mb-3">
        Click an example to load its profile into the calculator and render
        its net-income chart instantly.
      </p>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {data.households.map((h, i) => {
          const isGain = h.net_income_change > 0;
          const isSelected = selectedLabel === h.label;
          return (
            <button
              key={i}
              type="button"
              onClick={() =>
                onSelect(
                  {
                    label: h.label,
                    income: h.income,
                    age_head: h.age_head,
                    married: h.married,
                    dependents: h.dependents,
                  },
                  toImpactResponse(h),
                )
              }
              className={`text-left rounded-lg border p-4 transition-all hover:shadow-md ${
                isSelected
                  ? 'ring-2 ring-primary-500 ring-offset-1 bg-white border-primary-500'
                  : isGain
                    ? 'bg-primary-50 border-primary-300 hover:border-primary-500'
                    : h.net_income_change < 0
                      ? 'bg-gray-50 border-gray-300 hover:border-gray-500'
                      : 'bg-gray-50 border-gray-300 hover:border-gray-400'
              }`}
            >
              <p className="text-sm font-semibold text-gray-800">{h.label}</p>
              <p
                className="text-2xl font-bold mt-1"
                style={{
                  color: isGain
                    ? 'var(--chart-positive)'
                    : h.net_income_change < 0
                      ? 'var(--chart-negative)'
                      : 'var(--text-secondary)',
                }}
              >
                {fmtSigned(h.net_income_change)}/year
              </p>

              <TaxChannelBreakdown
                coTaxChange={h.state_tax_change}
                federalTaxChange={h.federal_tax_change ?? 0}
              />

              <p className="text-xs text-gray-500 mt-2 leading-5">
                CO tax: {fmtCurrency(h.baseline.co_income_tax)} →{' '}
                {fmtCurrency(h.reform.co_income_tax)}
              </p>
            </button>
          );
        })}
      </div>
      <p className="text-[11px] text-gray-500 italic mt-2">
        Income change is the Initiative 195 graduated schedule (2027) minus
        current law, so a negative value indicates a larger tax bill. Single
        parent files head of household. Married couples file jointly with the
        spouse aged 35.
      </p>
    </div>
  );
}

/** Splits the total impact into its two channels:
 *  - Colorado income tax change (the graduated schedule itself)
 *  - Federal income tax change (driven by SALT flow-through and other
 *    federal interactions with state tax)
 *
 *  Tax-change values use the "reform minus baseline" sign convention:
 *  a positive value indicates an increase in tax liability under the
 *  graduated schedule. The raw delta is displayed so a positive number
 *  corresponds to a tax increase, but the color coding is inverted so
 *  an increase reads as a cost (red) and a decrease reads as savings
 *  (green). */
function TaxChannelBreakdown({
  coTaxChange,
  federalTaxChange,
}: {
  coTaxChange: number;
  federalTaxChange: number;
}) {
  if (Math.abs(coTaxChange) < 1 && Math.abs(federalTaxChange) < 1) {
    return null;
  }
  const rows = [
    {
      label: 'CO income tax',
      value: coTaxChange,
      title:
        'Change in Colorado individual income tax liability under the Initiative 195 graduated schedule compared with current law. A positive value indicates an increase in tax.',
    },
    {
      label: 'Federal income tax',
      value: federalTaxChange,
      title:
        'Change in federal individual income tax under the Initiative 195 graduated schedule compared with current law. Colorado income tax counts toward the federal itemized deduction for state and local taxes (subject to the SALT cap), so a change in Colorado tax can shift federal taxable income and therefore federal tax. A positive value indicates an increase in tax.',
    },
  ];

  return (
    <div className="mt-2 pt-2 border-t border-gray-200 space-y-1">
      <p className="text-[10px] uppercase tracking-wider text-gray-500 font-medium mb-1">
        By tax channel
      </p>
      {rows.map(({ label, value, title }) => (
        <div
          key={label}
          className="flex items-center justify-between text-xs"
          title={title}
        >
          <span className="text-gray-700">{label}</span>
          <span
            className="font-medium tabular-nums"
            style={{
              // Tax increase => HH loses => red. Tax decrease => HH gains => green.
              color:
                value > 0
                  ? 'var(--chart-negative)'
                  : value < 0
                    ? 'var(--chart-positive)'
                    : 'var(--text-muted)',
            }}
          >
            {fmtSigned(value)}
          </span>
        </div>
      ))}
    </div>
  );
}
