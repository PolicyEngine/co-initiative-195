'use client';

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import { useHouseholdImpact } from '@/hooks/useHouseholdImpact';
import type {
  HouseholdImpactResponse,
  HouseholdRequest,
} from '@/lib/types';
import { CO_DASHBOARD_YEAR } from '@/lib/household';
import ChartWatermark from './ChartWatermark';

interface Props {
  request: HouseholdRequest | null;
  triggered: boolean;
  maxEarnings?: number;
  /** When supplied, the chart renders this precomputed payload instead
   * of firing a live /us/calculate request. */
  precomputed?: HouseholdImpactResponse | null;
}

interface ChartRow {
  income: number;
  benefit: number;
  federalTaxChange: number;
  stateTaxChange: number;
  netIncomeChange: number;
}

const formatCurrency = (value: number) =>
  `$${Math.round(value).toLocaleString('en-US')}`;
const formatCurrencyWithSign = (value: number) => {
  const formatted = formatCurrency(Math.abs(value));
  if (value > 0) return `+${formatted}`;
  if (value < 0) return `-${formatted}`;
  return formatted;
};
const formatIncome = (value: number) => {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  return `$${(value / 1000).toFixed(0)}k`;
};

function HoverTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ payload: ChartRow }>;
  label?: number;
}) {
  if (!active || !payload || !payload.length) return null;
  const p = payload[0].payload;
  const incomeLabel = typeof label === 'number' ? label : p.income;
  return (
    <div
      style={{
        background: 'var(--chart-tooltip-bg, #fff)',
        border: '1px solid var(--chart-tooltip-border, #e5e7eb)',
        borderRadius: 4,
        padding: '8px 12px',
        fontFamily: 'var(--font-sans)',
        fontSize: 12,
        minWidth: 240,
      }}
    >
      <p style={{ margin: '0 0 4px', fontWeight: 600 }}>
        Income: {formatCurrency(Math.round(incomeLabel / 100) * 100)}
      </p>
      <p
        style={{
          margin: '4px 0 2px',
          fontSize: 11,
          color: 'var(--text-muted)',
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
        }}
      >
        By tax channel
      </p>
      <p
        style={{ margin: 0 }}
        title="Change in Colorado individual income tax liability under the Initiative 195 graduated schedule compared with current law. A positive value indicates an increase in tax."
      >
        CO tax change: {formatCurrencyWithSign(p.stateTaxChange)}
      </p>
      <p
        style={{ margin: 0 }}
        title="Change in federal individual income tax under the Initiative 195 graduated schedule compared with current law. Colorado income tax counts toward the federal itemized deduction for state and local taxes (subject to the SALT cap), so a change in Colorado tax can shift federal taxable income and therefore federal tax. A positive value indicates an increase in tax."
      >
        Federal tax change: {formatCurrencyWithSign(p.federalTaxChange)}
      </p>
      <p style={{ margin: '4px 0 0', fontWeight: 600 }}>
        Net income change: {formatCurrencyWithSign(p.netIncomeChange)}
      </p>
    </div>
  );
}

export default function ImpactAnalysis({
  request,
  triggered,
  maxEarnings,
  precomputed,
}: Props) {
  const liveQuery = useHouseholdImpact(request, triggered && !precomputed);
  const data = precomputed ?? liveQuery.data;
  const isLoading = !precomputed && liveQuery.isLoading;
  const error = precomputed ? null : liveQuery.error;

  if (!triggered) return null;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <div className="inline-block h-12 w-12 animate-spin rounded-full border-4 border-solid border-primary border-r-transparent"></div>
          <p className="mt-4 text-gray-600">Calculating impact...</p>
        </div>
      </div>
    );
  }

  if (error) {
    const errorMessage = (error as Error).message;
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
        <h2 className="text-yellow-800 font-semibold mb-2">
          Household calculator temporarily unavailable
        </h2>
        <p className="text-yellow-700">
          The PolicyEngine API returned an error: <code>{errorMessage}</code>. You
          can still see precomputed results in the example-household cards above
          or on the <strong>Statewide impact</strong> tab.
        </p>
      </div>
    );
  }

  if (!data) return null;

  const benefitData = data.benefit_at_income;

  const federalTaxChangePoint = benefitData.federal_tax_change;
  const stateTaxChangePoint = benefitData.state_tax_change;
  const netIncomeChangePoint = benefitData.net_income_change;

  const xMax = maxEarnings ?? data.x_axis_max;

  const federalTaxChangeSeries = data.federalTaxChange;
  const stateTaxChangeSeries = data.stateTaxChange;
  const netIncomeChangeSeries = data.netIncomeChange;

  const chartData: ChartRow[] = data.income_range
    .map((inc, i) => ({
      income: inc,
      benefit: netIncomeChangeSeries[i],
      federalTaxChange: federalTaxChangeSeries[i],
      stateTaxChange: stateTaxChangeSeries[i],
      netIncomeChange: netIncomeChangeSeries[i],
    }))
    .filter((d) => d.income <= xMax);

  const metricCard = (
    label: string,
    value: number,
    inverseSign: boolean = false,
  ) => {
    const householdSign = inverseSign ? -value : value;
    const positive = householdSign > 0;
    const negative = householdSign < 0;
    return (
      <div
        className={`rounded-lg p-6 border ${
          positive
            ? 'bg-green-50 border-success'
            : negative
            ? 'bg-red-50 border-red-300'
            : 'bg-gray-50 border-gray-300'
        }`}
      >
        <p className="text-sm text-gray-700 mb-2">{label}</p>
        <p
          className={`text-3xl font-bold ${
            positive ? 'text-green-600' : negative ? 'text-red-600' : 'text-gray-600'
          }`}
        >
          {value !== 0 ? `${formatCurrencyWithSign(value)}/year` : '$0/year'}
        </p>
      </div>
    );
  };

  return (
    <div className="space-y-8">
      <h2 className="text-2xl font-bold text-primary">Impact analysis</h2>

      {/* Personal impact */}
      <div>
        <h3 className="text-xl font-bold text-gray-800 mb-4">
          Your household&apos;s estimated impact from Initiative 195 ({request?.year ?? CO_DASHBOARD_YEAR})
        </h3>
        <p className="text-gray-600 mb-4">
          Based on your employment income of <strong>{formatCurrency(request?.income ?? 0)}</strong>,
          comparing the Initiative 195 graduated schedule (reform) with current
          law (4.4% flat tax). Impact = reform &minus; baseline.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {metricCard('Federal tax change', federalTaxChangePoint, true)}
          {metricCard(
            'Colorado state tax change',
            stateTaxChangePoint,
            true,
          )}
          {metricCard('Net income change', netIncomeChangePoint)}
        </div>
      </div>

      <hr className="border-gray-200" />

      {/* Chart */}
      <div className="bg-white border rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-1 text-gray-800">
          Change in net income under Initiative 195
        </h3>
        <p className="text-sm text-gray-500 mb-4">
          Graduated schedule (reform) vs. current law (4.4% flat tax), by
          employment income
        </p>
        <ResponsiveContainer width="100%" height={400}>
            <LineChart data={chartData} margin={{ left: 20, right: 20, top: 5, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
              <XAxis
                dataKey="income"
                type="number"
                tickFormatter={formatIncome}
                stroke="var(--chart-reference)"
                domain={[0, xMax]}
                allowDataOverflow={false}
              />
              <YAxis tickFormatter={formatCurrency} stroke="var(--chart-reference)" width={80} />
              <Tooltip content={<HoverTooltip />} />
              <Legend />
              <ReferenceLine y={0} stroke="var(--chart-reference)" strokeWidth={2} />
              <Line
                type="monotone"
                dataKey="benefit"
                stroke="var(--chart-positive)"
                strokeWidth={3}
                name="Net income change"
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        <ChartWatermark />
        <p className="text-[11px] text-gray-500 italic mt-2">
          A value below the zero line means the household&apos;s net income
          falls (its tax rises) under the graduated schedule; a value above
          the line means net income rises.
        </p>
      </div>
    </div>
  );
}
